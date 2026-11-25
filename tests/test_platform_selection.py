from __future__ import annotations

import pytest

from nexus.platforms.selection import architecture_id, platform_id
from nexus.utils.exceptions import UnsupportedPlatformError


@pytest.mark.parametrize(("input_platform", "expected"), [("win32", "windows"), ("darwin", "macos")])
def test_supported_platform_ids(input_platform: str, expected: str) -> None:
    assert platform_id(input_platform) == expected


def test_unsupported_platform_is_explicit() -> None:
    with pytest.raises(UnsupportedPlatformError, match="linux"):
        platform_id("linux")


@pytest.mark.parametrize(
    ("machine", "expected"),
    [("arm64", "arm64"), ("aarch64", "arm64"), ("AMD64", "x64"), ("x86_64", "x64")],
)
def test_architecture_normalization(machine: str, expected: str) -> None:
    assert architecture_id(machine) == expected
