"""Network throughput per adapter, with a stable primary-link choice.

Selecting "the" adapter from raw counters alone flaps whenever two adapters are
nearly idle. NEXUS therefore prefers physical links and only switches away from
the current primary when another adapter clearly and repeatedly carries more
traffic.
"""

from __future__ import annotations

import logging
import time

import psutil

from nexus.core.metrics import NetworkAdapter, NetworkMetrics, RateTracker

log = logging.getLogger(__name__)

# A small constant makes an idle physical link win over an idle VPN/virtual
# link, without hiding real traffic on a virtual adapter.
_PHYSICAL_BONUS = 64.0 * 1024.0
_SWITCH_FACTOR = 1.75
_SWITCH_MARGIN = 128.0 * 1024.0
_SWITCH_SAMPLES = 2


def _is_virtual(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in ("loopback", "tailscale", "vpn", "virtual", "vethernet", "bluetooth")
    )


class NetworkCollector:
    def __init__(self) -> None:
        self._rates: dict[str, tuple[RateTracker, RateTracker]] = {}
        self._primary: str | None = None
        self._challenger: str | None = None
        self._challenger_hits = 0

    def sample(self) -> NetworkMetrics:
        now = time.monotonic()
        try:
            counters = psutil.net_io_counters(pernic=True)
        except Exception as exc:
            log.warning("Network counters unavailable: %s", exc)
            return NetworkMetrics()
        try:
            stats = psutil.net_if_stats()
        except Exception:
            stats = {}

        adapters: list[NetworkAdapter] = []
        candidates: dict[str, tuple[float, float, int, int, float | None]] = {}
        for name, counter in counters.items():
            if name.lower().startswith("loopback"):
                continue
            if name not in self._rates:
                self._rates[name] = (RateTracker(), RateTracker())
            down_tracker, up_tracker = self._rates[name]
            down = down_tracker.update(float(counter.bytes_recv), now)
            up = up_tracker.update(float(counter.bytes_sent), now)
            stat = stats.get(name)
            is_up = bool(stat.isup) if stat is not None else True
            speed = float(stat.speed) if stat is not None and stat.speed else None
            adapters.append(
                NetworkAdapter(
                    name=name,
                    received_bytes_per_sec=down,
                    sent_bytes_per_sec=up,
                    total_received_bytes=int(counter.bytes_recv),
                    total_sent_bytes=int(counter.bytes_sent),
                    link_speed_mbps=speed,
                    is_up=is_up,
                )
            )
            if is_up:
                candidates[name] = (
                    down,
                    up,
                    int(counter.bytes_recv),
                    int(counter.bytes_sent),
                    speed,
                )

        primary = self._select_primary(candidates)
        adapters.sort(
            key=lambda a: (
                -(a.received_bytes_per_sec or 0) - (a.sent_bytes_per_sec or 0),
                a.name,
            )
        )
        if primary is None:
            self._primary = None
            return NetworkMetrics(adapters=tuple(adapters))
        down, up, total_rx, total_tx, speed = candidates[primary]
        return NetworkMetrics(
            interface=primary,
            download_bytes_per_sec=down,
            upload_bytes_per_sec=up,
            total_received_bytes=total_rx,
            total_sent_bytes=total_tx,
            adapters=tuple(adapters),
            link_speed_mbps=speed,
        )

    @staticmethod
    def _score(name: str, candidate: tuple[float, float, int, int, float | None]) -> float:
        down, up, *_ = candidate
        score = (down or 0.0) + (up or 0.0)
        if not _is_virtual(name):
            score += _PHYSICAL_BONUS
        return score

    def _select_primary(self, candidates: dict[str, tuple[float, float, int, int, float | None]]) -> str | None:
        if not candidates:
            self._primary = None
            self._challenger = None
            self._challenger_hits = 0
            return None
        best = max(candidates, key=lambda name: (self._score(name, candidates[name]), name))
        current = self._primary
        if current is None or current not in candidates:
            return self._adopt(best, candidates)

        current_score = self._score(current, candidates[current])
        best_score = self._score(best, candidates[best])
        if best == current:
            self._challenger = None
            self._challenger_hits = 0
            return current

        # Recover quickly if the current link is virtual and a physical link is
        # healthy, or when the current link is effectively idle.
        if _is_virtual(current) and not _is_virtual(best):
            return self._adopt(best, candidates)
        if current_score < _PHYSICAL_BONUS and best_score >= _PHYSICAL_BONUS:
            return self._adopt(best, candidates)

        clearly_better = best_score > max(
            current_score * _SWITCH_FACTOR, current_score + _SWITCH_MARGIN
        )
        if clearly_better:
            if self._challenger == best:
                self._challenger_hits += 1
            else:
                self._challenger = best
                self._challenger_hits = 1
            if self._challenger_hits >= _SWITCH_SAMPLES:
                return self._adopt(best, candidates)
            return current

        self._challenger = None
        self._challenger_hits = 0
        return current

    def _adopt(self, name: str, candidates: dict[str, tuple[float, float, int, int, float | None]]) -> str:
        if name != self._primary:
            log.debug("Primary network adapter is now %s.", name)
        self._primary = name
        self._challenger = None
        self._challenger_hits = 0
        return name
