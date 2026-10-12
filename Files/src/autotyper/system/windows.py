"""
Windows backend: SendInput with Unicode key events.

This is "normal keyboard input" for the target app (the same mechanism on-screen
keyboards and IMEs use), so it works in Google Docs (Chrome/Edge/Firefox), Word,
Notepad and any standard text field. Enter and Tab are sent as real keys.
"""

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

from .base import InputBackend

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
GA_ROOT = 2

# Virtual-key codes for the keys that can be chosen as the stop shortcut
VK_CODES = {f"F{i}": 0x6F + i for i in range(1, 13)}  # F1=0x70 ... F12=0x7B
VK_CODES["Esc"] = 0x1B
VK_CODES["Pause"] = 0x13


@dataclass(frozen=True)
class KeyEvent:
    vk: int
    scan: int
    flags: int


def utf16_units(ch):
    data = ch.encode("utf-16-le")  # characters outside the BMP become surrogate pairs
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def plan_char(ch):
    """Low-level key events needed to type `ch` (pure function, testable anywhere)."""
    if ch == "\n":
        return [KeyEvent(VK_RETURN, 0, 0), KeyEvent(VK_RETURN, 0, KEYEVENTF_KEYUP)]
    if ch == "\t":
        return [KeyEvent(VK_TAB, 0, 0), KeyEvent(VK_TAB, 0, KEYEVENTF_KEYUP)]
    events = []
    for unit in utf16_units(ch):
        events.append(KeyEvent(0, unit, KEYEVENTF_UNICODE))
        events.append(KeyEvent(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    return events


def plan_backspace():
    """Key events for one Backspace press (pure function, testable anywhere)."""
    return [KeyEvent(VK_BACK, 0, 0), KeyEvent(VK_BACK, 0, KEYEVENTF_KEYUP)]


ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _InputUnion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _InputUnion)]


def _load_user32():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    user32.GetAncestor.restype = wintypes.HWND
    return user32


class WindowsBackend(InputBackend):
    name = "windows"
    needs_permissions = False
    fn_key_hint = False
    stop_keys = tuple(VK_CODES)

    def __init__(self, user32=None):
        if user32 is None:
            if sys.platform != "win32":
                raise RuntimeError("WindowsBackend can only be created on Windows")
            user32 = _load_user32()
        self._user32 = user32

    def prepare_process(self):
        try:  # finer sleep granularity -> smoother typing rhythm
            ctypes.WinDLL("winmm").timeBeginPeriod(1)
        except Exception:
            pass
        try:  # taskbar groups/uses our own icon instead of python.exe's
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AutoTyper.App")
        except Exception:
            pass
        try:  # lets the installer detect a running AutoTyper (Inno Setup AppMutex)
            self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "AutoTyper.SingleInstance")
        except Exception:
            self._mutex = None

    def send_char(self, ch):
        self._send_events(plan_char(ch))

    def send_backspace(self):
        self._send_events(plan_backspace())

    def _send_events(self, events):
        arr = (INPUT * len(events))()
        for i, ev in enumerate(events):
            arr[i].type = INPUT_KEYBOARD
            arr[i].ki = KEYBDINPUT(ev.vk, ev.scan, ev.flags, 0, 0)
        sent = self._user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))
        if sent != len(events):
            raise OSError("Windows blocked the keyboard input. If the target app runs as "
                          "administrator, run AutoTyper as administrator too.")

    def is_stop_key_down(self, key_name):
        vk = VK_CODES.get(key_name)
        if vk is None:
            return False
        return bool(self._user32.GetAsyncKeyState(vk) & 0x8000)

    def foreground_token(self):
        fg = self._user32.GetForegroundWindow()
        if not fg:
            return None
        root = self._user32.GetAncestor(fg, GA_ROOT) or fg
        return int(root)

    def is_own_window_foreground(self, window_id):
        fg = self._user32.GetForegroundWindow()
        if not fg:
            return False
        root = self._user32.GetAncestor(fg, GA_ROOT) or fg
        return int(root) == int(window_id)
