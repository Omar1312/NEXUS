"""Application exception hierarchy.

Every exception raised deliberately by NEXUS derives from :class:`NexusError`
so the UI can distinguish expected operational failures from programming bugs.
"""

from __future__ import annotations


class NexusError(Exception):
    """Base class for expected NEXUS failures."""

    user_message = "An unexpected application error occurred."

    def __init__(self, message: str = "", *, user_message: str | None = None) -> None:
        super().__init__(message or user_message or self.user_message)
        if user_message:
            self.user_message = user_message


class CollectionError(NexusError):
    """A metrics collector failed to produce data."""

    user_message = "System metrics could not be collected."


class SensorUnavailable(NexusError):
    """A requested sensor or metric is not exposed by this machine."""

    user_message = "This sensor is not available on this system."


class SettingsValidationError(NexusError):
    """A setting value is outside its supported range or type."""

    user_message = "One or more settings are invalid."


class DatabaseError(NexusError):
    """Persistent storage is unavailable or corrupt."""

    user_message = "The local performance database could not be used."


class ScanCancelled(NexusError):
    """A long-running scan was cancelled by the user."""

    user_message = "Scan cancelled."


class StartupEntryError(NexusError):
    """A startup entry could not be parsed."""

    user_message = "A startup entry could not be read."


class UnsupportedPlatformError(NexusError):
    """The current platform is unsupported or lacks the requested capability."""

    user_message = "This NEXUS feature is not supported on this operating system."
