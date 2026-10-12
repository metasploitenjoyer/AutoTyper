"""Chooses the keyboard backend that matches the operating system."""

import sys

from .base import DEFAULT_STOP_KEY, InputBackend, PermissionStatus, UnsupportedBackend

__all__ = ["DEFAULT_STOP_KEY", "InputBackend", "PermissionStatus",
           "platform_key", "backend_class", "create_backend"]


def platform_key(platform=None):
    """'windows', 'macos' or 'unsupported' for a sys.platform value."""
    p = platform or sys.platform
    if p.startswith("win"):
        return "windows"
    if p == "darwin":
        return "macos"
    return "unsupported"


def backend_class(platform=None):
    key = platform_key(platform)
    if key == "windows":
        from .windows import WindowsBackend
        return WindowsBackend
    if key == "macos":
        from .macos import MacBackend
        return MacBackend
    return UnsupportedBackend


def create_backend(platform=None):
    """Detect the OS and return the matching, ready-to-use backend."""
    return backend_class(platform)()
