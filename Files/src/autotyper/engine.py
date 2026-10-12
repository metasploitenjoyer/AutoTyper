"""
Typing engine: session control (countdown, timing, pause/resume, stop, safety checks).

Deliberately free of GUI code and OS-specific code so it can be unit-tested anywhere.
The real keyboard is injected (`send_char`, `send_backspace`); the clock and sleep
functions are injectable too (the tests use a virtual clock and a fake editor).
"""

import math
import threading
import time

from .humanize import HumanProfile
from .plan import TypoConfig, build_schedule, plan_steps  # noqa: F401  (build_schedule is re-exported)

PAUSE_SLICE = 0.005           # waits wake up this often (s) to look for stop / pause requests
FOCUS_POLL = 0.05             # how often the active window is compared with the target (s)
MAX_CONSECUTIVE_FAILURES = 5  # give up if the keyboard backend keeps failing
STOP_MESSAGE = "Stopped."


def typing_speed(chars, seconds):
    """Approximate speed as (characters per second, words per minute); 1 word = 5 chars."""
    if chars <= 0 or seconds <= 0:
        return 0.0, 0.0
    cps = chars / seconds
    return cps, cps * 60.0 / 5.0


def fmt_time(seconds):
    """Format seconds as m:ss (rounded up), e.g. 251.2 -> '4:12'."""
    s = max(0, int(math.ceil(seconds - 1e-9)))
    return f"{s // 60}:{s % 60:02d}"


def make_own_window_guard(message, *checks):
    """Build an `abort_check` that returns `message` while AutoTyper itself is the
    active window (any check returns True), so text is never typed into AutoTyper."""
    def guard():
        for check in checks:
            try:
                if check():
                    return message
            except Exception:
                continue
        return None
    return guard


class TypingSession:
    IDLE = "idle"
    COUNTDOWN = "countdown"
    TYPING = "typing"
    PAUSED = "paused"
    RESUMING = "resuming"
    DONE = "done"
    STOPPED = "stopped"
    ERROR = "error"
    ACTIVE = (COUNTDOWN, TYPING, PAUSED, RESUMING)

    def __init__(self, text, duration, send_char, *, countdown=5,
                 stop_check=None, abort_check=None, variation=1.0,
                 profile=None, typos=None, send_backspace=None,
                 pause_check=None, own_window_check=None,
                 own_window_message="AutoTyper is the active window.",
                 focus_token=None, stop_on_focus_change=True, resume_countdown=3,
                 clock=time.perf_counter, sleep=time.sleep, rng=None):
        """
        text                 text to type (line breaks as "\\n"); never modified
        duration             seconds the whole text should take
        send_char            callable(ch) that types one character
        send_backspace       callable() that presses Backspace (needed for typo simulation)
        countdown            seconds to wait before typing (time to click into the target)
        stop_check           callable() -> bool; polled constantly ("is the stop key down?")
        pause_check          callable() -> bool; "is the pause key down?" (each press toggles)
        abort_check          callable() -> str|None; a reason string stops typing
        own_window_check     callable() -> bool; True while AutoTyper itself is the active
                             window. Typing never starts then, and typing in progress pauses.
        focus_token          callable() -> hashable|None; identifies the active window. If it
                             changes while typing, the session stops (never types elsewhere).
        variation / profile  natural-rhythm settings (profile wins over variation)
        typos                TypoConfig for simulated mistakes and corrections
        """
        if not text:
            raise ValueError("text is empty")
        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        self.typos = (typos or TypoConfig()).bounded()
        if self.typos.enabled and self.typos.rate > 0 and send_backspace is None:
            raise ValueError("send_backspace is required to simulate typos")
        self.text = text
        self.duration = float(duration)
        self.total = len(text)
        self.variation = variation
        self.profile = profile
        self._send_char = send_char
        self._send_backspace = send_backspace
        self._countdown = max(0, int(countdown))
        self._resume_countdown_s = max(0, int(resume_countdown))
        self._stop_check = stop_check
        self._abort_check = abort_check
        self._pause_check = pause_check
        self._own_window_check = own_window_check
        self._own_window_message = own_window_message
        self._focus_token = focus_token
        self._stop_on_focus = bool(stop_on_focus_change) or (self.typos.enabled and self.typos.rate > 0)
        self._clock = clock
        self._sleep = sleep
        self._rng = rng

        self._stop_event = threading.Event()
        self._pause_requested = False
        self._resume_requested = False
        self._pause_prev = False
        self._thread = None
        self._t_start = None
        self._t_end = None
        self._pause_started = None
        self._target = None
        self._last_focus_check = -1e9

        self.state = self.IDLE
        self.cause = ""          # for STOPPED: "user" | "abort" | "focus"
        self.message = ""
        self.pause_reason = ""   # "user" | "own_window"
        self.typed = 0           # original characters correctly in place
        self.skipped = 0
        self.pending = 0         # characters of a simulated mistake currently on screen
        self.stray = 0           # mistake characters left behind when the session ended
        self.typos_made = 0
        self.countdown_left = 0

    # ---- public API ----------------------------------------------------
    @property
    def is_running(self):
        return self.state in self.ACTIVE

    @property
    def is_paused(self):
        return self.state in (self.PAUSED, self.RESUMING)

    def start(self):
        """Run in a background thread (used by the GUI)."""
        self.state = self.COUNTDOWN
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self):
        """Request an immediate stop. Safe to call from any thread."""
        self._stop_event.set()

    def pause(self):
        """Pause typing (takes effect before the next keystroke)."""
        if self.state == self.TYPING:
            self._pause_requested = True

    def resume(self):
        """Resume after a pause (a short countdown lets you click back into your app)."""
        if self.state == self.PAUSED:
            self._resume_requested = True

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)

    def _now_eff(self):
        if self._t_end is not None:
            return self._t_end
        if self._pause_started is not None:
            return self._pause_started
        return self._clock()

    def elapsed(self):
        """Seconds spent typing (pauses excluded; frozen once the session ended)."""
        if self._t_start is None:
            return 0.0
        return max(0.0, self._now_eff() - self._t_start)

    def remaining(self):
        """Estimated seconds of typing time left (frozen while paused and after the end)."""
        if self.state == self.DONE:
            return 0.0
        if self._t_start is None:
            return self.duration
        return max(0.0, self.duration - (self._now_eff() - self._t_start))

    def run(self):
        """Run synchronously until finished or stopped."""
        try:
            self._run()
        except Exception as exc:  # never let the worker die silently
            self._end(self.ERROR, f"Error: {exc}", stray=self.pending)

    # ---- helpers -------------------------------------------------------
    def _stopped(self):
        if self._stop_event.is_set():
            return True
        if self._stop_check is not None and self._stop_check():
            self._stop_event.set()
            return True
        return False

    def _wait_until(self, t_abs):
        """Sleep until clock() reaches t_abs (stop only). False if stop was requested."""
        while True:
            if self._stopped():
                return False
            left = t_abs - self._clock()
            if left <= 0:
                return True
            self._sleep(min(left, PAUSE_SLICE))

    def _end(self, state, message, cause="", stray=0):
        self._t_end = self._clock()
        self.message = message
        self.cause = cause
        self.stray = stray
        self.state = state

    def _abort_reason(self):
        return self._abort_check() if self._abort_check else None

    def _own_window(self):
        return bool(self._own_window_check and self._own_window_check())

    def _token(self):
        if self._focus_token is None:
            return None
        try:
            return self._focus_token()
        except Exception:
            return None

    def _poll_pause_toggle(self):
        """True once per press of the pause key."""
        if self._pause_check is None:
            return False
        down = bool(self._pause_check())
        pressed = down and not self._pause_prev
        self._pause_prev = down
        return pressed

    def _focus_changed(self):
        if not self._stop_on_focus or self._focus_token is None:
            return False
        now = self._clock()
        if now - self._last_focus_check < FOCUS_POLL:
            return False
        self._last_focus_check = now
        token = self._token()
        if token is None:
            return False
        if self._target is None:
            self._target = token
            return False
        return token != self._target

    # ---- waiting for a step (stop / pause / focus aware) ---------------
    def _wait_step(self, at):
        """Wait until the step is due. Returns 'go', 'stop' or 'focus'."""
        while True:
            if self._stopped():
                return "stop"
            if self._poll_pause_toggle():
                self._pause_requested = True
            if self._pause_requested:
                outcome = self._pause("user")
                if outcome != "ok":
                    return outcome
                continue
            if self._own_window():
                outcome = self._pause("own_window")  # never type into AutoTyper: wait instead
                if outcome != "ok":
                    return outcome
                continue
            if self._focus_changed():
                return "focus"
            left = self._t_start + at - self._clock()
            if left <= 0:
                return "go"
            self._sleep(min(left, PAUSE_SLICE))

    def _pause(self, reason):
        self.pause_reason = reason
        self._resume_requested = False
        pause_start = self._clock()
        self._pause_started = pause_start
        self.state = self.PAUSED
        while True:
            if self._stopped():
                return "stop"
            if self._poll_pause_toggle():
                self._resume_requested = True
            if self._resume_requested:
                self._resume_requested = False
                outcome = self._resume_sequence()
                if outcome == "again":
                    self.pause_reason = "own_window"
                    self.state = self.PAUSED
                    continue
                if outcome != "ok":
                    return outcome
                break
            self._sleep(PAUSE_SLICE)
        self._t_start += self._clock() - pause_start  # pauses never eat into the schedule
        self._pause_started = None
        self._pause_requested = False
        self.pause_reason = ""
        self.state = self.TYPING
        return "ok"

    def _resume_sequence(self):
        """Countdown after Resume so the user can click back into the target app."""
        self.state = self.RESUMING
        t0 = self._clock()
        for n in range(self._resume_countdown_s, 0, -1):
            self.countdown_left = n
            if not self._wait_until(t0 + (self._resume_countdown_s - n + 1)):
                return "stop"
        self.countdown_left = 0
        if self._own_window():
            return "again"
        token = self._token()
        if token is not None:
            if self.pending == 0:
                self._target = token            # nothing half-typed: allow a new target window
            elif self._stop_on_focus and token != self._target:
                return "focus"                  # a correction is pending: never move elsewhere
        return "ok"

    # ---- ending ----------------------------------------------------------
    def _cleanup_pending(self):
        """After a user stop in the middle of a simulated mistake, remove exactly those
        characters (only if the cursor is certainly still in the same field)."""
        if self.pending <= 0 or self._send_backspace is None:
            return self.pending
        if self._own_window():
            return self.pending                  # keys would go to AutoTyper itself
        if self._stop_on_focus:
            token = self._token()
            if token is not None and self._target is not None and token != self._target:
                return self.pending
        while self.pending > 0:
            try:
                self._send_backspace()
            except Exception:
                break
            self.pending -= 1
        return self.pending

    def _finish_stop(self):
        self._end(self.STOPPED, STOP_MESSAGE, "user", self._cleanup_pending())

    # ---- main loop -------------------------------------------------------
    def _run(self):
        self.state = self.COUNTDOWN
        t0 = self._clock()
        for n in range(self._countdown, 0, -1):
            self.countdown_left = n
            if not self._wait_until(t0 + (self._countdown - n + 1)):
                return self._end(self.STOPPED, STOP_MESSAGE, "user")
        self.countdown_left = 0

        reason = self._abort_reason()
        if reason:
            return self._end(self.STOPPED, reason, "abort")
        if self._own_window():
            return self._end(self.STOPPED, self._own_window_message, "abort")

        profile = self.profile if self.profile is not None else HumanProfile.from_variation(self.variation)
        steps = plan_steps(self.text, self.duration, profile, self.typos, self._rng)
        self._t_start = self._clock()
        self._target = self._token()
        self.state = self.TYPING
        failures = 0

        for step in steps:
            outcome = self._wait_step(step.at)
            if outcome == "stop":
                return self._finish_stop()
            if outcome == "focus":
                return self._end(self.STOPPED, "Stopped: the active window changed.", "focus", self.pending)
            reason = self._abort_reason()
            if reason:
                return self._end(self.STOPPED, reason, "abort", self.pending)
            if self._stopped():  # last look right before touching the keyboard
                return self._finish_stop()

            if step.kind == "backspace":
                if self.pending <= 0:
                    continue  # nothing of ours to delete: never touch existing text
                try:
                    self._send_backspace()
                except Exception as exc:
                    return self._end(self.ERROR, f"Could not perform a correction reliably: {exc}",
                                     stray=self.pending)
                self.pending -= 1
                if self.pending == 0:
                    self.typos_made += 1
            else:
                try:
                    self._send_char(step.ch)
                except Exception as exc:
                    if step.temp or self.pending > 0:
                        return self._end(self.ERROR, f"Could not perform a correction reliably: {exc}",
                                         stray=self.pending)
                    self.skipped += 1
                    failures += 1
                    if failures >= MAX_CONSECUTIVE_FAILURES:
                        return self._end(self.ERROR, f"Keyboard error: {exc}")
                else:
                    failures = 0
                    if step.temp:
                        self.pending += 1
            self.typed = max(self.typed, step.commit)

        note = f" ({self.skipped} unsupported character(s) skipped)" if self.skipped else ""
        self._end(self.DONE, f"Finished typing {self.typed:,} characters.{note}")
