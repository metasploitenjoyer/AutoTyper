"""Common interface for the per-platform keyboard backends."""

from dataclasses import dataclass

DEFAULT_STOP_KEY = "F8"
FUNCTION_KEYS = [f"F{i}" for i in range(1, 13)]


@dataclass(frozen=True)
class PermissionStatus:
    """macOS needs Accessibility (to type) and, for a global stop key, Input Monitoring."""
    accessibility: bool = True
    input_monitoring: bool = True


class InputBackend:
    """What the rest of the app needs from the operating system."""

    name = "base"
    needs_permissions = False   # True on macOS
    fn_key_hint = False         # True where F-keys may need the Fn key (Mac laptops)
    stop_keys = tuple(FUNCTION_KEYS) + ("Esc",)

    def prepare_process(self):
        """One-time process setup (timer resolution, taskbar identity...)."""

    def send_char(self, ch):
        """Type one character as real keyboard input. Raise OSError on failure."""
        raise NotImplementedError

    def send_backspace(self):
        """Press Backspace once (used only to undo characters AutoTyper itself typed)."""
        raise NotImplementedError

    def foreground_token(self):
        """Comparable identifier of the active window/app, or None if it cannot be read."""
        return None

    def is_stop_key_down(self, key_name):
        """True while the given key is physically held (works in any active app)."""
        return False

    def available_stop_keys(self):
        return list(self.stop_keys)

    def permissions(self):
        return PermissionStatus()

    def request_permissions(self):
        """Ask the OS to show its permission prompt (macOS)."""

    def open_permission_settings(self, which="accessibility"):
        """Open the OS page where the permission can be granted (macOS)."""

    def is_own_window_foreground(self, window_id):
        """True/False if the OS can tell whether our window is in front; None if unknown."""
        return None


class UnsupportedBackend(InputBackend):
    """Used on systems other than Windows/macOS so the UI can still be explored."""

    name = "unsupported"

    def send_char(self, ch):
        raise OSError("AutoTyper can type on Windows and macOS only.")

    def send_backspace(self):
        raise OSError("AutoTyper can type on Windows and macOS only.")
