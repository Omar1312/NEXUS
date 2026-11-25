"""Minimal PDH query for the real current CPU clock.

``psutil.cpu_freq()`` reports the nominal/base frequency on Windows (a constant),
so NEXUS combines it with the PDH ``% Processor Performance`` counter to show the
actual current clock. The counter returns the percentage of nominal performance
that the processor is running at, which is also how Task Manager reports it.

Everything here degrades to ``None`` when PDH or the counter is unavailable.
"""

from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes

log = logging.getLogger(__name__)

PDH_FMT_DOUBLE = 0x0000_0200
PDH_CSTATUS_VALID_DATA = 0x0000_0000
PDH_CSTATUS_NEW_DATA = 0x0000_0001
ERROR_SUCCESS = 0

_TOTAL_PERFORMANCE_PATH = r"\Processor Information(_Total)\% Processor Performance"


class _PdhCounterValue(ctypes.Structure):
    _fields_ = [("status", wintypes.DWORD), ("value", ctypes.c_double)]


class _PdhQuery:
    """One lazily-created PDH query that must be sampled repeatedly."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._query: ctypes.c_void_p | None = None
        self._counter: ctypes.c_void_p | None = None
        self._pdh: ctypes.WinDLL | None = None
        self._primed = False
        self._failed = False

    def _open(self) -> bool:
        try:
            pdh = ctypes.WinDLL("pdh.dll")
        except OSError:
            self._failed = True
            return False
        pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p)]
        pdh.PdhOpenQueryW.restype = wintypes.LONG
        add_counter = getattr(pdh, "PdhAddEnglishCounterW", None) or getattr(pdh, "PdhAddCounterW", None)
        add_counter.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p)]
        add_counter.restype = wintypes.LONG
        pdh.PdhCollectQueryData.argtypes = [ctypes.c_void_p]
        pdh.PdhCollectQueryData.restype = wintypes.LONG
        pdh.PdhGetFormattedCounterValue.argtypes = [
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(_PdhCounterValue),
        ]
        pdh.PdhGetFormattedCounterValue.restype = wintypes.LONG
        pdh.PdhCloseQuery.argtypes = [ctypes.c_void_p]
        pdh.PdhCloseQuery.restype = wintypes.LONG

        query = ctypes.c_void_p()
        if pdh.PdhOpenQueryW(None, 0, ctypes.byref(query)) != ERROR_SUCCESS:
            self._failed = True
            return False
        counter = ctypes.c_void_p()
        if add_counter(query, _TOTAL_PERFORMANCE_PATH, 0, ctypes.byref(counter)) != ERROR_SUCCESS:
            pdh.PdhCloseQuery(query)
            self._failed = True
            return False
        self._pdh, self._query, self._counter = pdh, query, counter
        return True

    def read_percent(self) -> float | None:
        """Return current processor performance in percent, or ``None``."""
        if self._failed:
            return None
        with self._lock:
            if self._pdh is None and not self._open():
                return None
            assert self._pdh is not None and self._query is not None and self._counter is not None
            if self._pdh.PdhCollectQueryData(self._query) != ERROR_SUCCESS:
                return None
            if not self._primed:
                # The first PDH sample only establishes a baseline.
                self._primed = True
                return None
            value = _PdhCounterValue()
            value_type = wintypes.DWORD()
            if (
                self._pdh.PdhGetFormattedCounterValue(
                    self._counter, PDH_FMT_DOUBLE, ctypes.byref(value_type), ctypes.byref(value)
                )
                != ERROR_SUCCESS
            ):
                return None
            if value.status not in (PDH_CSTATUS_VALID_DATA, PDH_CSTATUS_NEW_DATA):
                return None
            percent = float(value.value)
            if percent <= 0.0 or percent > 1000.0:
                return None
            return percent

    def close(self) -> None:
        with self._lock:
            if self._pdh is not None and self._query is not None:
                try:
                    self._pdh.PdhCloseQuery(self._query)
                except OSError:
                    pass
            self._pdh = None
            self._query = None
            self._counter = None

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.close()
        except Exception:
            pass
