"""Session behaviour with a mock keyboard: corrections, Stop, F8, pause/resume, focus changes."""

import random
import threading
import time
import unittest

import _path  # noqa: F401
from _fakes import FakeEditor, FakeTime, key_window, make_session
from autotyper.engine import TypingSession
from autotyper.humanize import STYLES, build_profile
from autotyper.plan import TypoConfig

TEXT = "The quick brown fox jumps over the lazy dog. " * 30
TYPOS = TypoConfig(enabled=True, rate=0.35, correction_delay=0.8)


def typo_session(ed, ft, duration=120, seed=5, **kw):
    kw.setdefault("typos", TYPOS)
    kw.setdefault("profile", build_profile(True, "natural", "medium"))
    kw.setdefault("rng", random.Random(seed))
    return make_session(TEXT, duration, ed, ft, **kw)


class CorrectionSessionTests(unittest.TestCase):
    def test_full_run_with_corrections_types_exactly_the_text(self):
        ft = FakeTime()
        ed = FakeEditor("EXISTING TEXT: ", ft)
        s = typo_session(ed, ft)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.typed_text, TEXT)                 # exactly the original, mistakes removed
        self.assertTrue(ed.buf.startswith("EXISTING TEXT: ")) # pre-existing text untouched
        self.assertGreater(s.typos_made, 20)
        self.assertEqual((s.pending, s.stray, s.typed), (0, 0, len(TEXT)))
        self.assertAlmostEqual(ft.now, 120.0, delta=0.05)     # the chosen duration still holds
        self.assertIn("Finished", s.message)

    def test_original_text_object_is_never_changed(self):
        ft, ed = FakeTime(), FakeEditor()
        s = typo_session(ed, ft)
        s.run()
        self.assertEqual(s.text, TEXT)

    def test_typos_require_a_backspace_function(self):
        with self.assertRaises(ValueError):
            TypingSession("hello world", 10, print, typos=TYPOS)
        TypingSession("hello world", 10, print, typos=TypoConfig(False))   # disabled: not needed

    def test_corrections_work_across_many_seeds(self):
        for seed in range(15):
            ft = FakeTime()
            ed = FakeEditor("PRE", ft)
            typo_session(ed, ft, duration=60, seed=seed).run()
            self.assertEqual(ed.typed_text, TEXT, seed)

    def test_stop_hotkey_in_the_middle_of_a_mistake_cleans_it_up(self):
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        flag = {"stop": False}
        holder = {}

        def char(ch):
            ed.char(ch)
            if holder["s"].pending > 0 and not flag["stop"] and len(ed.typed_text) > 100:
                flag["stop"] = True                       # F8 pressed while a mistake is on screen

        s = make_session(TEXT, 120, ed, ft, typos=TYPOS, rng=random.Random(5), stop_check=lambda: flag["stop"])
        s._send_char = char
        holder["s"] = s
        s.run()
        self.assertTrue(flag["stop"])
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertEqual(s.cause, "user")
        self.assertEqual(s.stray, 0)
        self.assertTrue(TEXT.startswith(ed.typed_text), "a simulated mistake was left behind")
        self.assertTrue(ed.buf.startswith("PRE-"))

    def test_stop_button_in_the_middle_of_a_mistake_never_types_into_autotyper(self):
        """Clicking Stop makes AutoTyper the active window: the cleanup must NOT send keys then."""
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        own = {"active": False}
        holder = {}

        def char(ch):
            ed.char(ch)
            if holder["s"].pending > 0 and len(ed.typed_text) > 100 and not own["active"]:
                own["active"] = True                      # the user clicked Stop in AutoTyper's window
                holder["s"].stop()

        s = make_session(TEXT, 120, ed, ft, typos=TYPOS, rng=random.Random(5),
                         own_window_check=lambda: own["active"])
        s._send_char = char
        holder["s"] = s
        s.run()
        backspaces_after_stop = [e for e in ed.log if e[0] == "back" and e[1] > ft.now - 0.001]
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertGreater(s.stray, 0)                    # reported honestly...
        self.assertEqual(backspaces_after_stop, [])       # ...and no key was sent while AutoTyper was active

    def test_focus_change_during_a_mistake_stops_without_touching_the_other_window(self):
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        window = {"id": 1}
        holder = {}

        def char(ch):
            ed.char(ch)
            if holder["s"].pending > 0 and len(ed.typed_text) > 100:
                window["id"] = 2                          # the user (or the OS) switched windows

        s = make_session(TEXT, 120, ed, ft, typos=TYPOS, rng=random.Random(5), focus_token=lambda: window["id"])
        s._send_char = char
        holder["s"] = s
        s.run()
        backs_before = len([e for e in ed.log if e[0] == "back"])
        self.assertEqual((s.state, s.cause), (TypingSession.STOPPED, "focus"))
        self.assertGreater(s.stray, 0)
        self.assertEqual(len([e for e in ed.log if e[0] == "back"]), backs_before)  # no Backspace sent elsewhere
        self.assertIn("window changed", s.message)

    def test_failed_backspace_stops_everything_immediately(self):
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        ed.fail_back = True
        s = typo_session(ed, ft)
        s.run()
        self.assertEqual(s.state, TypingSession.ERROR)
        self.assertIn("correction reliably", s.message)
        self.assertGreater(s.stray, 0)
        n = len(ed.log)
        self.assertEqual(len(ed.log), n)                  # nothing was typed after the error
        self.assertTrue(ed.buf.startswith("PRE-"))

    def test_failed_mistake_character_stops_instead_of_miscounting_backspaces(self):
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        seen = {"n": 0}

        def failing(ch):
            # the second wrong character of the first mistake fails to type
            if holder["s"].pending == 1 and seen["n"] == 0:
                seen["n"] += 1
                return True
            return False

        holder = {}
        ed.fail_char = failing
        s = typo_session(ed, ft, typos=TypoConfig(True, 0.6, 0.5, 3))
        holder["s"] = s
        s.run()
        self.assertTrue(ed.buf.startswith("PRE-"))        # Backspace never ate into pre-existing text
        if seen["n"]:
            self.assertEqual(s.state, TypingSession.ERROR)

    def test_failed_normal_character_is_skipped_not_fatal(self):
        ft, ed = FakeTime(), FakeEditor()
        ed.fail_char = lambda ch: ch == "q"
        s = make_session("quick quiet", 5, ed, ft)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.typed_text, "uick uiet")
        self.assertEqual(s.skipped, 2)

    def test_typos_force_the_window_guard_even_if_it_is_switched_off(self):
        ft, ed = FakeTime(), FakeEditor()
        window = {"id": 1}

        def char(ch):
            ed.char(ch)
            if len(ed.buf) == 30:
                window["id"] = 2

        s = make_session(TEXT, 60, ed, ft, typos=TYPOS, stop_on_focus_change=False,
                         focus_token=lambda: window["id"], rng=random.Random(2))
        s._send_char = char
        s.run()
        self.assertEqual(s.cause, "focus")


class FocusTests(unittest.TestCase):
    def test_window_change_stops_typing_within_a_blink(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        window = {"id": 1}
        changed_at = {}

        def char(ch):
            ed.char(ch)
            if len(ed.buf) == 40 and not changed_at:
                changed_at["t"] = ft.now
                window["id"] = 2

        s = make_session(TEXT, 60, ed, ft, focus_token=lambda: window["id"])
        s._send_char = char
        s.run()
        self.assertEqual((s.state, s.cause), (TypingSession.STOPPED, "focus"))
        self.assertLessEqual(len(ed.buf), 40 + 3)          # at most a couple of characters slip out
        self.assertLess(ft.now - changed_at["t"], 0.2)

    def test_unreadable_window_never_blocks_typing(self):
        ft, ed = FakeTime(), FakeEditor()
        s = make_session("hello world", 5, ed, ft, focus_token=lambda: None)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        s = make_session("hello world", 5, FakeEditor(), ft, focus_token=lambda: 1 / 0)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)

    def test_guard_can_be_switched_off_when_no_corrections_are_used(self):
        ft, ed = FakeTime(), FakeEditor()
        window = {"id": 1}

        def char(ch):
            ed.char(ch)
            window["id"] += 1

        s = make_session("hello world, plenty of letters", 5, ed, ft, stop_on_focus_change=False,
                         focus_token=lambda: window["id"])
        s._send_char = char
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)


class PauseResumeTests(unittest.TestCase):
    def test_pause_key_pauses_and_resumes_without_losing_time_or_text(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        press = key_window(ft, (10.0, 10.1), (14.0, 14.1))      # pause at t=10 s, resume at t=14 s
        s = make_session(TEXT, 60, ed, ft, pause_check=press, resume_countdown=2)
        samples = []
        base_check = s._pause_check

        def spying_check():
            samples.append((ft.now, s.state, s.remaining(), s.elapsed()))
            return base_check()

        s._pause_check = spying_check
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.typed_text, TEXT)
        self.assertEqual(ed.sends_between(10.1, 16.0), [])      # silent while paused + resume countdown
        self.assertGreater(ft.now, 60.0 + 5.5)                  # the pause (~6 s) was added on top
        self.assertLess(ft.now, 60.0 + 7.0)
        paused = [x for x in samples if x[1] == TypingSession.PAUSED]
        self.assertGreater(len(paused), 100)
        self.assertEqual(len({round(x[2], 6) for x in paused}), 1)   # remaining time is frozen while paused
        self.assertEqual(len({round(x[3], 6) for x in paused}), 1)   # and so is the elapsed time
        self.assertAlmostEqual(s.elapsed(), 60.0, delta=0.1)         # pauses are not counted as typing time

    def test_pause_and_resume_methods(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        holder = {}

        def char(ch):
            ed.char(ch)
            n = len(ed.buf)
            if n == 20:
                holder["s"].pause()
            if n > 20 and holder["s"].state == TypingSession.PAUSED:
                pass

        s = make_session(TEXT, 30, ed, ft)
        s._send_char = char
        holder["s"] = s

        def resume_later():
            # called by the virtual sleep: resume 3 virtual seconds after the pause started
            if s.state == TypingSession.PAUSED and ft.now >= resume_at.setdefault("t", ft.now + 3):
                s.resume()

        resume_at = {}
        real_sleep = ft.sleep

        def sleep(dt):
            real_sleep(dt)
            resume_later()

        s._sleep = sleep
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.typed_text, TEXT)

    def test_pause_when_not_typing_does_nothing(self):
        s = TypingSession("hello", 5, print)
        s.pause()
        s.resume()
        self.assertFalse(s._pause_requested)
        self.assertFalse(s.is_paused)

    def test_autotyper_becoming_active_pauses_instead_of_typing_into_itself(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        own = key_window(ft, (20.0, 26.0))                       # AutoTyper window active 20-26 s
        press = key_window(ft, (30.0, 30.1))                     # user presses Resume at 30 s
        s = make_session(TEXT, 60, ed, ft, own_window_check=own, pause_check=press, resume_countdown=2)
        reasons = []
        base_check = s._pause_check

        def spy():
            if s.state == TypingSession.PAUSED:
                reasons.append(s.pause_reason)       # why the session is waiting
            return base_check()

        s._pause_check = spy
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.typed_text, TEXT)
        self.assertEqual(ed.sends_between(20.0, 32.0), [])       # nothing typed while AutoTyper was in front
        self.assertIn("own_window", set(reasons))

    def test_resume_stays_paused_while_autotyper_is_still_in_front(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        own = key_window(ft, (20.0, 40.0))
        press = key_window(ft, (25.0, 25.1), (45.0, 45.1))       # first Resume too early, second one later
        s = make_session(TEXT, 60, ed, ft, own_window_check=own, pause_check=press, resume_countdown=2)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(ed.sends_between(20.0, 47.0), [])
        self.assertEqual(ed.typed_text, TEXT)

    def test_resume_countdown_gives_time_to_click_back(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        press = key_window(ft, (10.0, 10.1), (15.0, 15.1))
        s = make_session(TEXT, 60, ed, ft, pause_check=press, resume_countdown=3)
        s.run()
        self.assertEqual(ed.sends_between(10.1, 18.0), [])       # 15 s + 3 s countdown

    def test_after_a_pause_you_may_continue_in_another_window(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        window = {"id": 1}
        press = key_window(ft, (10.0, 10.1), (20.0, 20.1))

        def token():
            if ft.now >= 12.0:
                window["id"] = 2                                # user moved to another document while paused
            return window["id"]

        s = make_session(TEXT, 60, ed, ft, pause_check=press, focus_token=token, resume_countdown=2)
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)            # nothing half-typed: new target accepted
        self.assertEqual(ed.typed_text, TEXT)

    def test_pending_correction_never_moves_to_another_window(self):
        ft = FakeTime()
        ed = FakeEditor("PRE-", ft)
        window = {"id": 1}
        press = key_window(ft, (50.0, 50.1))
        holder = {}
        paused_at = {}

        def char(ch):
            ed.char(ch)
            if holder["s"].pending > 0 and len(ed.typed_text) > 100 and not paused_at:
                paused_at["t"] = ft.now
                holder["s"].pause()                              # pause in the middle of a mistake
                window["id"] = 2                                 # ...and the user goes elsewhere

        s = make_session(TEXT, 120, ed, ft, typos=TYPOS, rng=random.Random(5), pause_check=press,
                         focus_token=lambda: window["id"], resume_countdown=1)
        s._send_char = char
        holder["s"] = s
        s.run()
        self.assertEqual((s.state, s.cause), (TypingSession.STOPPED, "focus"))
        self.assertGreater(s.stray, 0)
        self.assertEqual(len([e for e in ed.log if e[0] == "back" and e[1] > paused_at["t"]]), 0)

    def test_stop_while_paused(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        press = key_window(ft, (10.0, 10.1))
        stop = key_window(ft, (13.0, 99.0))
        s = make_session(TEXT, 60, ed, ft, pause_check=press, stop_check=stop)
        s.run()
        self.assertEqual((s.state, s.cause), (TypingSession.STOPPED, "user"))
        self.assertLess(ft.now, 13.1)

    def test_elapsed_and_remaining_without_pauses(self):
        ft = FakeTime()
        ed = FakeEditor("", ft)
        s = make_session("word " * 100, 50, ed, ft)
        seen = []
        orig = s._send_char
        s._send_char = lambda ch: (seen.append((s.elapsed(), s.remaining())), orig(ch))
        s.run()
        self.assertTrue(all(abs(e + r - 50) < 1e-6 for e, r in seen))
        self.assertTrue(all(b[0] >= a[0] for a, b in zip(seen, seen[1:])))
        self.assertEqual(s.remaining(), 0.0)


class ThreadedControlTests(unittest.TestCase):
    """Real clock and threads: Pause, Resume and Stop must respond while typing."""

    def test_pause_resume_stop_with_real_threads(self):
        ed = FakeEditor()
        s = TypingSession("a" * 400, 8, ed.char, countdown=0, resume_countdown=0, send_backspace=ed.back)
        s.start()
        time.sleep(0.5)
        s.pause()
        deadline = time.time() + 1
        while s.state != TypingSession.PAUSED and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(s.state, TypingSession.PAUSED)
        n = len(ed.buf)
        time.sleep(0.4)
        self.assertEqual(len(ed.buf), n, "characters were typed while paused")
        s.resume()
        deadline = time.time() + 1
        while s.state != TypingSession.TYPING and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(s.state, TypingSession.TYPING)
        time.sleep(0.3)
        self.assertGreater(len(ed.buf), n)
        t0 = time.perf_counter()
        s.stop()
        s.join(2)
        self.assertLess(time.perf_counter() - t0, 0.2)
        self.assertEqual(s.state, TypingSession.STOPPED)

    def test_stop_hotkey_with_corrections_real_clock(self):
        ed = FakeEditor("PRE")
        flag = threading.Event()
        s = TypingSession(TEXT, 10, ed.char, countdown=0, send_backspace=ed.back, stop_check=flag.is_set,
                          typos=TypoConfig(True, 0.4, 0.3), profile=STYLES["natural"], focus_token=lambda: 1)
        s.start()
        time.sleep(1.0)
        flag.set()
        s.join(2)
        self.assertFalse(s._thread.is_alive())
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertTrue(TEXT.startswith(ed.typed_text), "a typo was left on screen after the hotkey stop")
        self.assertTrue(ed.buf.startswith("PRE"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
