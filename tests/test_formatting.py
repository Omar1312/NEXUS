"""Tests for formatting helpers."""

from __future__ import annotations

import pytest

from nexus.utils import formatting


class TestFormatBytes:
    def test_zero(self):
        assert formatting.format_bytes(0) == "0 B"

    def test_none(self):
        assert formatting.format_bytes(None) == formatting.UNAVAILABLE

    def test_negative(self):
        assert formatting.format_bytes(-1) == formatting.UNAVAILABLE

    def test_bytes(self):
        assert formatting.format_bytes(512) == "512 B"

    def test_kib(self):
        assert formatting.format_bytes(2048) == "2.0 KiB"

    def test_mib(self):
        assert formatting.format_bytes(2 * 1024 * 1024) == "2.0 MiB"

    def test_gib(self):
        assert formatting.format_bytes(1.5 * 1024 * 1024 * 1024) == "1.5 GiB"

    def test_invalid_value(self):
        assert formatting.format_bytes("abc") == formatting.UNAVAILABLE


class TestFormatRate:
    def test_zero(self):
        assert formatting.format_rate(0) == "0 B/s"

    def test_none(self):
        assert formatting.format_rate(None) == formatting.UNAVAILABLE

    def test_negative(self):
        assert formatting.format_rate(-1) == formatting.UNAVAILABLE

    def test_rate(self):
        assert formatting.format_rate(2048) == "2.0 KiB/s"


class TestFormatBitrate:
    def test_zero(self):
        assert formatting.format_bitrate(0) == "0 bit/s"

    def test_none(self):
        assert formatting.format_bitrate(None) == formatting.UNAVAILABLE

    def test_mbit(self):
        # 1250000 bytes/s * 8 = 10 Mbit/s
        assert formatting.format_bitrate(1_250_000) == "10.0 Mbit/s"


class TestFormatPercent:
    def test_none(self):
        assert formatting.format_percent(None) == formatting.UNAVAILABLE

    def test_clamps_high(self):
        assert formatting.format_percent(150) == "100%"

    def test_clamped_low(self):
        assert formatting.format_percent(-10) == "0%"

    def test_value(self):
        assert formatting.format_percent(73.4) == "73%"


class TestFormatFrequency:
    def test_none(self):
        assert formatting.format_frequency(None) == formatting.UNAVAILABLE

    def test_mhz(self):
        assert formatting.format_frequency(800) == "800 MHz"

    def test_converts_mhz_to_ghz(self):
        assert formatting.format_frequency(2400) == "2.40 GHz"

    def test_ghz(self):
        assert formatting.format_frequency(3200) == "3.20 GHz"


class TestFormatTemperature:
    def test_none(self):
        assert formatting.format_temperature(None) == formatting.UNAVAILABLE

    def test_value(self):
        assert formatting.format_temperature(65.5) == "66 °C"


class TestFormatPower:
    def test_none(self):
        assert formatting.format_power(None) == formatting.UNAVAILABLE

    def test_value(self):
        assert formatting.format_power(12.5) == "12.5 W"


class TestFormatDuration:
    def test_none(self):
        assert formatting.format_duration(None) == formatting.UNAVAILABLE

    def test_seconds(self):
        assert formatting.format_duration(30) == "30s"

    def test_minutes(self):
        assert formatting.format_duration(125) == "2m 05s"

    def test_hours(self):
        assert formatting.format_duration(3700) == "1h 01m"

    def test_days(self):
        assert formatting.format_duration(90000) == "1d 01h"


class TestClamp:
    def test_within_range(self):
        assert formatting.clamp(5, 0, 10) == 5

    def test_below_min(self):
        assert formatting.clamp(-5, 0, 10) == 0

    def test_above_max(self):
        assert formatting.clamp(15, 0, 10) == 10
