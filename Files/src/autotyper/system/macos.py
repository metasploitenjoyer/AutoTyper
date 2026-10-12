"""
macOS backend: Quartz keyboard events (CGEvent) through ctypes - no extra packages.

Typing other apps requires the Accessibility permission. The stop key is read by
polling the global key state, which needs Input Monitoring on recent macOS versions.
"""

import ctypes
import ctypes.util
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from .base import InputBackend, PermissionStatus

KVK_RETURN = 36
KVK_TAB = 48
KVK_DELETE = 51   # the Backspace key on a Mac keyboard
KEYCODES = {
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97,
    "F7": 98, "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111,
    "Esc": 53,
}
HID_EVENT_TAP = 0                # kCGHIDEventTap
HID_SYSTEM_STATE = 1             # kCGEventSourceStateHIDSystemState

SETTINGS_URLS = {
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
}


@dataclass(frozen=True)
class KeyPress:
    """One key press (down + up). `text` set -> type that Unicode text with this event."""
    keycode: int
    text: Optional[str] = None


def plan_char(ch):
    """Key presses needed to type `ch` (pure function, testable anywhere)."""
    if ch == "\n":
        return [KeyPress(KVK_RETURN)]
    if ch == "\t":
        return [KeyPress(KVK_TAB)]
    return [KeyPress(0, ch)]


def plan_backspace():
    """Key press for one Backspace (pure function, testable anywhere)."""
    return [KeyPress(KVK_DELETE)]


def _frontmost_pid_native():
    """Process id of the frontmost app via the Objective-C runtime (no extra packages).
    Returns None when it cannot be read."""
    try:
        objc_path = ctypes.util.find_library("objc")
        appkit_path = ctypes.util.find_library("AppKit")
        if not objc_path or not appkit_path:
            return None
        objc = ctypes.cdll.LoadLibrary(objc_path)
        ctypes.cdll.LoadLibrary(appkit_path)  # registers NSWorkspace
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        send_obj = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        send_int = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(address)
        sel = objc.sel_registerName
        workspace = send_obj(objc.objc_getClass(b"NSWorkspace"), sel(b"sharedWorkspace"))
        app = send_obj(workspace, sel(b"frontmostApplication"))
        if not app:
            return None
        return int(send_int(app, sel(b"processIdentifier")))
    except Exception:
        return None


def _load_libs():
    path = ctypes.util.find_library("ApplicationServices")
    cf_path = ctypes.util.find_library("CoreFoundation")
    if not path or not cf_path:
        raise OSError("macOS frameworks not found")
    cg = ctypes.CDLL(path)
    cf = ctypes.CDLL(cf_path)

    cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    cg.CGEventCreateKeyboardEvent.argtypes = (ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool)
    cg.CGEventKeyboardSetUnicodeString.restype = None
    cg.CGEventKeyboardSetUnicodeString.argtypes = (
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_uint16))
    cg.CGEventSetFlags.restype = None
    cg.CGEventSetFlags.argtypes = (ctypes.c_void_p, ctypes.c_uint64)
    cg.CGEventPost.restype = None
    cg.CGEventPost.argtypes = (ctypes.c_uint32, ctypes.c_void_p)
    cg.CGEventSourceKeyState.restype = ctypes.c_bool
    cg.CGEventSourceKeyState.argtypes = (ctypes.c_int32, ctypes.c_uint16)
    cg.AXIsProcessTrusted.restype = ctypes.c_bool
    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = (ctypes.c_void_p,)
    return cg, cf


class MacBackend(InputBackend):
    name = "macos"
    needs_permissions = True
    fn_key_hint = True
    stop_keys = tuple(KEYCODES)

    def __init__(self, cg=None, cf=None, frontmost_pid=None):
        if cg is None or cf is None:
            if sys.platform != "darwin":
                raise RuntimeError("MacBackend can only be created on macOS")
            cg, cf = _load_libs()
        self._cg = cg
        self._cf = cf
        self._frontmost_pid = frontmost_pid or _frontmost_pid_native

    # ---- typing --------------------------------------------------------
    def send_char(self, ch):
        for press in plan_char(ch):
            self._post_press(press)

    def send_backspace(self):
        for press in plan_backspace():
            self._post_press(press)

    def foreground_token(self):
        return self._frontmost_pid()

    def _post_press(self, press):
        for key_down in (True, False):
            event = self._cg.CGEventCreateKeyboardEvent(None, press.keycode, key_down)
            if not event:
                raise OSError("Could not create a keyboard event")
            try:
                if press.text is not None:
                    data = press.text.encode("utf-16-le")
                    units = (ctypes.c_uint16 * (len(data) // 2)).from_buffer_copy(data)
                    self._cg.CGEventKeyboardSetUnicodeString(event, len(units), units)
                self._cg.CGEventSetFlags(event, 0)  # ignore modifiers physically held down
                self._cg.CGEventPost(HID_EVENT_TAP, event)
            finally:
                self._cf.CFRelease(event)

    # ---- stop key --------------------------------------------------------
    def is_stop_key_down(self, key_name):
        code = KEYCODES.get(key_name)
        if code is None:
            return False
        return bool(self._cg.CGEventSourceKeyState(HID_SYSTEM_STATE, code))

    # ---- permissions -----------------------------------------------------
    def _optional(self, name, default):
        try:
            fn = getattr(self._cg, name)
        except AttributeError:  # older macOS without this API
            return default
        try:
            fn.restype = ctypes.c_bool
        except Exception:
            pass
        return fn()

    def permissions(self):
        accessibility = bool(self._cg.AXIsProcessTrusted())
        input_monitoring = bool(self._optional("CGPreflightListenEventAccess", True))
        return PermissionStatus(accessibility, input_monitoring)

    def request_permissions(self):
        self._optional("CGRequestPostEventAccess", True)

    def open_permission_settings(self, which="accessibility"):
        if which == "input_monitoring":
            self._optional("CGRequestListenEventAccess", True)
        url = SETTINGS_URLS.get(which, SETTINGS_URLS["accessibility"])
        try:
            subprocess.Popen(["open", url])
        except OSError:
            pass
