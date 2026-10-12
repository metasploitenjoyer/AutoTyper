"""
Tests for the typing-speed calculation and the Stop / F8 behaviour.

Run from the project folder:   python -m unittest discover -s tests -v

Most tests use a virtual clock (instant + deterministic); the "Threaded" tests use the
real clock and real threads to prove that Stop / F8 really end a running session fast.
"""

import random
import statistics
import threading
import time
import unittest

import _path  # noqa: F401  (adds ../src to sys.path)
from autotyper.engine import (TypingSession, build_schedule, fmt_time,  # noqa: E402
                              make_own_window_guard, typing_speed)


class FakeTime:
    """Virtual clock: sleep() just advances time, so a 10-minute run takes milliseconds."""

    def __init__(self):
        self.now = 0.0

    def clock(self):
        return self.now

    def sleep(self, dt):
        self.now += max(dt, 0.0)


def make_session(text, duration, send, ft, **kw):
    return TypingSession(text, duration, send, clock=ft.clock, sleep=ft.sleep, **kw)


# --------------------------------------------------------------------------
class ScheduleTests(unittest.TestCase):
    def test_example_from_spec_1000_chars_5_minutes(self):
        text = "x" * 1000
        sched = build_schedule(text, 300, random.Random(1))
        self.assertEqual(len(sched), 1000)
        self.assertAlmostEqual(sched[-1], 300.0, places=6)
        delays = [b - a for a, b in zip([0.0] + sched, sched)]
        self.assertAlmostEqual(statistics.mean(delays), 0.3, places=6)  # 300 s / 1000 chars

    def test_last_character_lands_on_the_duration(self):
        for n, secs in [(1, 5), (7, 30), (350, 60), (2000, 120), (5000, 600), (1000, 1)]:
            sched = build_schedule("a" * n, secs, random.Random(n))
            self.assertEqual(len(sched), n)
            self.assertAlmostEqual(sched[-1], secs, places=6, msg=f"{n} chars / {secs}s")

    def test_schedule_strictly_increasing(self):
        sched = build_schedule("Hello, world.\nNew line! " * 100, 90, random.Random(3))
        self.assertTrue(all(b > a for a, b in zip(sched, sched[1:])))
        self.assertGreater(sched[0], 0)

    def test_delays_vary(self):
        sched = build_schedule("abcdefghij" * 100, 100, random.Random(4))
        delays = [b - a for a, b in zip([0.0] + sched, sched)]
        self.assertGreater(statistics.stdev(delays), 0.1 * statistics.mean(delays))
        self.assertGreater(len({round(d, 6) for d in delays}), 900)  # essentially all distinct

    def test_pauses_are_longer_after_punctuation_and_line_breaks(self):
        text = "ab. cd\n" * 1500
        sched = build_schedule(text, 3000, random.Random(5))
        delays = [b - a for a, b in zip([0.0] + sched, sched)]

        def mean_for(ch):
            return statistics.mean(d for d, c in zip(delays, text) if c == ch)

        self.assertGreater(mean_for("."), 1.8 * mean_for("a"))
        self.assertGreater(mean_for("\n"), 2.2 * mean_for("a"))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            build_schedule("", 10)
        with self.assertRaises(ValueError):
            build_schedule("abc", 0)
        with self.assertRaises(ValueError):
            build_schedule("abc", -5)

    def test_fmt_time(self):
        self.assertEqual(fmt_time(0), "0:00")
        self.assertEqual(fmt_time(251.2), "4:12")
        self.assertEqual(fmt_time(60), "1:00")
        self.assertEqual(fmt_time(599.1), "10:00")
        self.assertEqual(fmt_time(-3), "0:00")


# --------------------------------------------------------------------------
class SessionTests(unittest.TestCase):
    def test_types_text_exactly(self):
        text = ("Hello, World!  Two spaces.\nSecond paragraph.\n\n\tTabbed line "
                "with CAPS, ñ, é, €, “quotes” — and numbers 12,345.67?")
        out, ft = [], FakeTime()
        s = make_session(text, 30, out.append, ft, countdown=0)
        s.run()
        self.assertEqual("".join(out), text)
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual((s.typed, s.total), (len(text), len(text)))
        self.assertEqual(s.remaining(), 0.0)

    def test_total_time_matches_duration_including_countdown_and_key_overhead(self):
        ft, out = FakeTime(), []

        def slow_send(ch):  # every keystroke costs 3 ms of "real" time
            out.append(ch)
            ft.now += 0.003

        text = "The quick brown fox jumps over the lazy dog. " * 40  # 1,800 chars
        s = make_session(text, 120, slow_send, ft, countdown=5, rng=random.Random(9))
        s.run()
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual("".join(out), text)
        # 5 s countdown + 120 s typing; absolute schedule means overhead doesn't accumulate
        self.assertAlmostEqual(ft.now, 125.0, delta=0.05)

    def test_countdown_runs_before_first_character(self):
        ft, first_time = FakeTime(), []
        s = make_session("abc", 3, lambda ch: first_time.append(ft.now) if not first_time else None,
                         ft, countdown=5)
        s.run()
        self.assertGreaterEqual(first_time[0], 5.0)

    def test_remaining_time_tracks_schedule(self):
        ft, text = FakeTime(), "word " * 400
        samples, holder = [], {}

        def send(ch):
            samples.append((len(samples), holder["s"].remaining()))

        s = make_session(text, 200, send, ft, countdown=0, rng=random.Random(11))
        holder["s"] = s
        s.run()
        expected = build_schedule(text, 200, random.Random(11))
        for i, rem in samples[::50]:
            self.assertAlmostEqual(rem, 200 - expected[i], delta=0.02)
        rems = [r for _, r in samples]
        self.assertTrue(all(b <= a for a, b in zip(rems, rems[1:])))  # only ever decreases

    def test_very_short_duration_still_completes(self):
        out, ft = [], FakeTime()
        s = make_session("x" * 1000, 0.5, out.append, ft, countdown=0)
        s.run()
        self.assertEqual(len(out), 1000)
        self.assertEqual(s.state, TypingSession.DONE)

    def test_single_character(self):
        out, ft = [], FakeTime()
        make_session("a", 10, out.append, ft, countdown=0).run()
        self.assertEqual(out, ["a"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            TypingSession("", 10, print)
        with self.assertRaises(ValueError):
            TypingSession("abc", 0, print)

    # ---- Stop button ---------------------------------------------------
    def test_stop_button_stops_before_next_character(self):
        out, ft, holder = [], FakeTime(), {}

        def send(ch):
            out.append(ch)
            if len(out) == 10:
                holder["s"].stop()  # Stop pressed while the 10th character is being typed

        s = make_session("a" * 500, 60, send, ft, countdown=0)
        holder["s"] = s
        s.run()
        self.assertEqual(len(out), 10)  # nothing typed after Stop
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertEqual(s.typed, 10)

    def test_stop_during_countdown_types_nothing(self):
        out, ft = [], FakeTime()
        s = make_session("abc", 10, out.append, ft, countdown=5)
        s.stop()
        s.run()
        self.assertEqual(out, [])
        self.assertEqual(s.state, TypingSession.STOPPED)

    # ---- F8 ------------------------------------------------------------
    def test_f8_check_stops_immediately(self):
        out, ft = [], FakeTime()
        # "F8 goes down" right after the 7th character was typed
        s = make_session("a" * 500, 60, out.append, ft, countdown=0,
                         stop_check=lambda: len(out) >= 7)
        s.run()
        self.assertEqual(len(out), 7)
        self.assertEqual(s.state, TypingSession.STOPPED)

    def test_f8_during_countdown(self):
        out, ft = [], FakeTime()
        s = make_session("abc", 10, out.append, ft, countdown=5,
                         stop_check=lambda: ft.now >= 2.0)
        s.run()
        self.assertEqual(out, [])
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertLess(ft.now, 2.1)

    # ---- safety guards -------------------------------------------------
    def test_abort_if_autotyper_window_is_active_at_start(self):
        out, ft = [], FakeTime()
        s = make_session("abc", 10, out.append, ft, countdown=1,
                         abort_check=lambda: "AutoTyper is the active window")
        s.run()
        self.assertEqual(out, [])
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertIn("active window", s.message)

    def test_abort_if_focus_returns_to_autotyper_midway(self):
        out, ft = [], FakeTime()
        s = make_session("a" * 100, 10, out.append, ft, countdown=0,
                         abort_check=lambda: "focus lost" if len(out) >= 3 else None)
        s.run()
        self.assertEqual(len(out), 3)
        self.assertEqual(s.state, TypingSession.STOPPED)

    def test_unsupported_character_is_skipped_not_fatal(self):
        out, ft = [], FakeTime()

        def send(ch):
            if ch == "€":
                raise ValueError("unsupported")
            out.append(ch)

        s = make_session("a€b€c", 5, send, ft, countdown=0)
        s.run()
        self.assertEqual("".join(out), "abc")
        self.assertEqual(s.state, TypingSession.DONE)
        self.assertEqual(s.skipped, 2)

    def test_keyboard_backend_broken_gives_error(self):
        ft = FakeTime()

        def send(ch):
            raise RuntimeError("no keyboard")

        s = make_session("a" * 50, 5, send, ft, countdown=0)
        s.run()
        self.assertEqual(s.state, TypingSession.ERROR)
        self.assertLess(s.typed, 50)


# --------------------------------------------------------------------------
class ThreadedRealTimeTests(unittest.TestCase):
    """Real clock + real threads: proves Stop / F8 work while a session is running."""

    def _run_and_stop(self, stopper, **kw):
        out = []
        s = TypingSession("a" * 300, 6, out.append, countdown=0, **kw)
        s.start()
        t_stop = {}

        def do_stop():
            t_stop["t"] = time.perf_counter()
            stopper(s)

        threading.Timer(0.5, do_stop).start()
        s.join(3)
        t_end = time.perf_counter()
        self.assertFalse(s._thread.is_alive(), "worker thread did not end")
        return s, out, t_end - t_stop["t"]

    def test_stop_button_while_typing(self):
        s, out, lag = self._run_and_stop(lambda sess: sess.stop())
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertLess(lag, 0.2)
        self.assertTrue(0 < len(out) < 300)
        n = len(out)
        time.sleep(0.3)
        self.assertEqual(len(out), n, "characters were typed after Stop")

    def test_f8_polling_while_typing(self):
        flag = threading.Event()
        s, out, lag = self._run_and_stop(lambda sess: flag.set(), stop_check=flag.is_set)
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertLess(lag, 0.2)
        self.assertLess(len(out), 300)

    def test_stop_during_real_countdown(self):
        out = []
        s = TypingSession("abc", 5, out.append, countdown=5)
        s.start()
        time.sleep(0.3)
        t0 = time.perf_counter()
        s.stop()
        s.join(2)
        self.assertLess(time.perf_counter() - t0, 0.2)
        self.assertEqual(out, [])
        self.assertEqual(s.state, TypingSession.STOPPED)

    def test_real_time_duration_is_accurate(self):
        out = []
        s = TypingSession("hello world. " * 10, 2.0, out.append, countdown=0)
        t0 = time.perf_counter()
        s.run()
        self.assertAlmostEqual(time.perf_counter() - t0, 2.0, delta=0.25)
        self.assertEqual(s.state, TypingSession.DONE)



# --------------------------------------------------------------------------
class VariationAndSpeedTests(unittest.TestCase):
    def test_zero_variation_is_perfectly_even(self):
        sched = build_schedule("Hello, world. Even rhythm!\n" * 20, 60, random.Random(1), variation=0)
        delays = [b - a for a, b in zip([0.0] + sched, sched)]
        self.assertLess(max(delays) - min(delays), 1e-9)
        self.assertAlmostEqual(sched[-1], 60.0, places=9)

    def test_more_variation_means_more_spread(self):
        def spread(v):
            sched = build_schedule("abcdefghij" * 100, 100, random.Random(7), variation=v)
            delays = [b - a for a, b in zip([0.0] + sched, sched)]
            return statistics.pstdev(delays)
        self.assertLess(spread(0.0), spread(0.3))
        self.assertLess(spread(0.3), spread(1.0))

    def test_every_variation_still_ends_on_the_duration(self):
        for v in (0, 0.25, 0.7, 1.0, 5, -2):  # out-of-range values are clamped
            sched = build_schedule("x" * 777, 123, random.Random(3), variation=v)
            self.assertAlmostEqual(sched[-1], 123.0, places=9)

    def test_session_passes_variation_through(self):
        out, ft = [], FakeTime()
        s = make_session("a" * 200, 20, out.append, ft, countdown=0, variation=0)
        times = []
        s._send_char = lambda ch: times.append(ft.now)
        s.run()
        gaps = [b - a for a, b in zip(times, times[1:])]
        self.assertLess(max(gaps) - min(gaps), 0.02)  # even rhythm (limited by the 5 ms sleep slice)

    def test_typing_speed_example_from_spec(self):
        cps, wpm = typing_speed(1000, 300)  # 1,000 characters in 5 minutes
        self.assertAlmostEqual(cps, 3.3333, places=3)
        self.assertAlmostEqual(wpm, 40.0, places=6)
        self.assertEqual(typing_speed(0, 10), (0.0, 0.0))
        self.assertEqual(typing_speed(10, 0), (0.0, 0.0))


class OwnWindowGuardTests(unittest.TestCase):
    def test_guard_blocks_while_autotyper_is_active(self):
        active = {"v": True}
        guard = make_own_window_guard("busy", lambda: active["v"])
        self.assertEqual(guard(), "busy")
        active["v"] = False
        self.assertIsNone(guard())

    def test_any_check_can_trigger_and_errors_are_ignored(self):
        def boom():
            raise RuntimeError("os call failed")
        self.assertIsNone(make_own_window_guard("busy", boom, lambda: False)())
        self.assertEqual(make_own_window_guard("busy", boom, lambda: True)(), "busy")

    def test_session_never_types_into_autotyper(self):
        out, ft = [], FakeTime()
        s = make_session("hello", 5, out.append, ft, countdown=2,
                         abort_check=make_own_window_guard("own window", lambda: True))
        s.run()
        self.assertEqual(out, [])
        self.assertEqual(s.state, TypingSession.STOPPED)
        self.assertEqual(s.cause, "abort")


if __name__ == "__main__":
    unittest.main(verbosity=2)
