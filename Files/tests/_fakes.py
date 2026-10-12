"""Shared test doubles: a virtual clock and a fake text editor (a mock keyboard target)."""

import _path  # noqa: F401
from autotyper.engine import TypingSession


class FakeTime:
    """Virtual clock: sleep() just advances time, so long runs finish instantly."""

    def __init__(self):
        self.now = 0.0

    def clock(self):
        return self.now

    def sleep(self, dt):
        self.now += max(dt, 0.0)


class FakeEditor:
    """Pretends to be a text field: applies typed characters and Backspace to a buffer.

    `pre` is text that already exists in the destination. Deleting any of it is a bug,
    so Backspace raises AssertionError if it ever would.
    """

    def __init__(self, pre="", clock=None):
        self.pre = pre
        self.buf = pre
        self.clock = clock
        self.log = []            # ("char"/"back", virtual time)
        self.fail_char = None    # callable(ch) -> bool: make that character fail
        self.fail_back = False

    def _stamp(self):
        return self.clock.now if self.clock else 0.0

    def char(self, ch):
        if self.fail_char and self.fail_char(ch):
            raise OSError("key press failed")
        self.buf += ch
        self.log.append(("char", self._stamp()))

    def back(self):
        if self.fail_back:
            raise OSError("backspace failed")
        assert len(self.buf) > len(self.pre), "Backspace would delete text that was already there!"
        self.buf = self.buf[:-1]
        self.log.append(("back", self._stamp()))

    @property
    def typed_text(self):
        return self.buf[len(self.pre):]

    def sends_between(self, t0, t1):
        return [e for e in self.log if t0 <= e[1] < t1]


def make_session(text, duration, editor, ft, **kw):
    kw.setdefault("countdown", 0)
    kw.setdefault("resume_countdown", 0)
    if "send_backspace" not in kw:
        kw["send_backspace"] = editor.back
    return TypingSession(text, duration, editor.char, clock=ft.clock, sleep=ft.sleep, **kw)


def key_window(ft, *windows):
    """pause_check / stop_check helper: True while the virtual time is inside any (start, end) window."""
    return lambda: any(a <= ft.now < b for a, b in windows)
