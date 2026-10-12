"""Humanization profiles and the typo/correction plan (pure planning, no timing loop)."""

import random
import statistics
import unittest

import _path  # noqa: F401
from _fakes import FakeEditor
from autotyper.humanize import (FLAT, LEVELS, MAX_JITTER, MAX_PAUSE, MAX_THINK, MAX_THINK_CHANCE, STYLES,
                                HumanProfile, build_profile, char_weight, pause_multiplier, scaled)
from autotyper.plan import NEIGHBORS, Step, TypoConfig, build_schedule, plan_steps

PROSE = ("The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs!\n\n"
         "Is this working? Yes, it is: numbers 12345, symbols #$% and ünïcödé stay untouched.\n") * 6


def delays(steps):
    return [b.at - a.at for a, b in zip([Step(0.0, "char")] + steps, steps)]


def replay(steps, pre=""):
    """Apply the plan to a fake editor; returns the editor."""
    ed = FakeEditor(pre)
    for s in steps:
        if s.kind == "char":
            ed.char(s.ch)
        else:
            ed.back()
    return ed


class HumanizeTests(unittest.TestCase):
    def test_styles_get_progressively_more_human(self):
        steady, natural, slow = (STYLES[k] for k in ("steady", "natural", "thoughtful"))
        self.assertLess(steady.jitter, natural.jitter)
        self.assertLess(natural.jitter, slow.jitter)
        self.assertLess(steady.sentence_pause, natural.sentence_pause)
        self.assertLess(natural.sentence_pause, slow.sentence_pause)
        self.assertEqual(steady.think_chance, 0.0)
        self.assertLess(natural.think_chance, slow.think_chance)

    def test_levels_scale_the_strength(self):
        low, med, high = (build_profile(True, "natural", lvl) for lvl in ("low", "medium", "high"))
        self.assertLess(low.jitter, med.jitter)
        self.assertLess(med.jitter, high.jitter)
        self.assertLess(low.sentence_pause, med.sentence_pause)
        self.assertLess(med.sentence_pause, high.sentence_pause)
        self.assertEqual(med, STYLES["natural"].bounded())   # Medium = the style as designed

    def test_disabled_is_perfectly_steady(self):
        self.assertIs(build_profile(False, "thoughtful", "high"), FLAT)
        steps = plan_steps("Hello, world. " * 40, 60, FLAT, None, random.Random(1))
        d = delays(steps)
        self.assertLess(max(d) - min(d), 1e-9)

    def test_custom_sliders(self):
        none = build_profile(True, "natural", "custom", variation=0, pauses=0, thinking=0)
        self.assertEqual((none.jitter, none.think_chance), (0.0, 0.0))
        self.assertEqual((none.word_pause, none.sentence_pause, none.paragraph_pause), (1.0, 1.0, 1.0))
        full = build_profile(True, "natural", "custom", variation=100, pauses=100, thinking=100)
        self.assertAlmostEqual(full.jitter, MAX_JITTER)
        self.assertAlmostEqual(full.think_chance, 0.05)
        self.assertGreater(full.sentence_pause, STYLES["natural"].sentence_pause)
        mid = build_profile(True, "natural", "custom", variation=50, pauses=50, thinking=0)
        self.assertAlmostEqual(mid.sentence_pause, STYLES["natural"].sentence_pause)  # 50 = the style's own

    def test_everything_is_bounded(self):
        wild = HumanProfile(jitter=50, word_pause=-3, punct_pause=999, sentence_pause=999,
                            paragraph_pause=999, think_chance=5, think_min=-1, think_max=999).bounded()
        self.assertEqual(wild.jitter, MAX_JITTER)
        self.assertEqual(wild.word_pause, 1.0)
        self.assertEqual((wild.punct_pause, wild.sentence_pause, wild.paragraph_pause), (MAX_PAUSE,) * 3)
        self.assertEqual(wild.think_chance, MAX_THINK_CHANCE)
        self.assertEqual((wild.think_min, wild.think_max), (1.0, MAX_THINK))
        for k in (0, 0.5, 1, 1.5, 100):
            sc = scaled(STYLES["thoughtful"], k)
            self.assertLessEqual(sc.jitter, MAX_JITTER)
            self.assertLessEqual(sc.sentence_pause, MAX_PAUSE)
            self.assertLessEqual(sc.think_chance, MAX_THINK_CHANCE)

    def test_every_keystroke_delay_stays_inside_its_bounds(self):
        rng = random.Random(3)
        for style, prof in STYLES.items():
            p = prof.bounded()
            for ch in "a .,!?\n":
                lo = (1 - p.jitter) * pause_multiplier(ch, p)
                hi = (1 + p.jitter) * pause_multiplier(ch, p) * (p.think_max if p.think_chance else 1)
                for _ in range(2000):
                    w = char_weight(ch, p, rng)
                    self.assertGreaterEqual(w, lo - 1e-9, (style, ch))
                    self.assertLessEqual(w, hi + 1e-9, (style, ch))

    def test_pauses_follow_words_punctuation_sentences_and_paragraphs(self):
        p = STYLES["natural"]
        self.assertEqual(pause_multiplier("a", p), 1.0)
        order = [pause_multiplier(c, p) for c in ("a", " ", ",", ".", "\n")]
        self.assertEqual(order, sorted(order))
        self.assertLess(order[0], order[1])                      # word pause > letter
        self.assertLess(order[2], order[3])                      # sentence pause > comma pause
        self.assertLess(order[3], order[4])                      # paragraph pause is the longest

    def test_thinking_pauses_exist_only_when_enabled(self):
        text = "word " * 4000
        def long_pauses(profile):
            d = delays(plan_steps(text, 4000, profile, None, random.Random(5)))
            med = statistics.median(d)
            return sum(1 for x in d if x > 2.9 * med * profile.word_pause * (1 + profile.jitter))
        self.assertEqual(long_pauses(STYLES["steady"].bounded()), 0)
        self.assertGreater(long_pauses(STYLES["thoughtful"].bounded()), 20)

    def test_chosen_duration_is_respected_for_every_style_and_level(self):
        for style in STYLES:
            for level in LEVELS:
                steps = plan_steps(PROSE, 90, build_profile(True, style, level), None, random.Random(2))
                self.assertAlmostEqual(steps[-1].at, 90.0, places=9, msg=(style, level))
                self.assertTrue(all(b.at > a.at for a, b in zip(steps, steps[1:])))

    def test_old_variation_api_still_works(self):
        self.assertEqual(HumanProfile.from_variation(1.0), HumanProfile())
        self.assertEqual(HumanProfile.from_variation(0).jitter, 0.0)
        self.assertEqual(len(build_schedule("hello", 5)), 5)


class NeighborTests(unittest.TestCase):
    def test_keyboard_neighbours(self):
        self.assertEqual(set(NEIGHBORS), set("abcdefghijklmnopqrstuvwxyz"))
        self.assertTrue({"q", "w", "s", "z"} <= set(NEIGHBORS["a"]))
        for ch, near in NEIGHBORS.items():
            self.assertNotIn(ch, near)
            self.assertGreaterEqual(len(near), 2)


class TypoPlanTests(unittest.TestCase):
    CFG = TypoConfig(enabled=True, rate=0.3, correction_delay=0.8, max_lookahead=2)

    def plan(self, text=PROSE, seed=1, duration=300, cfg=None, profile=None):
        return plan_steps(text, duration, profile or STYLES["natural"], cfg or self.CFG, random.Random(seed))

    def test_replaying_the_plan_gives_exactly_the_original_text(self):
        for seed in range(25):
            for text in (PROSE, "Hello world, this is a test.\nSecond line\twith tab.", "ab cd ef",
                         "naïve café — ¿qué tal? 😀 ok", "x" * 50 + " " + "y" * 50):
                steps = self.plan(text, seed)
                ed = replay(steps, pre="EXISTING: ")
                self.assertEqual(ed.typed_text, text, (seed, text[:20]))
                self.assertTrue(ed.buf.startswith("EXISTING: "))

    def test_typos_really_happen_and_use_all_three_kinds(self):
        self.assertGreater(len([s for s in self.plan(seed=4) if s.kind == "backspace"]), 10)
        from autotyper.plan import _plan_typos
        kinds = set()
        for seed in range(20):
            for ev in _plan_typos(PROSE, self.CFG, random.Random(seed)).values():
                self.assertNotEqual(ev.typed, ev.correct)
                if len(ev.typed) == len(ev.correct) + 1:
                    kinds.add("double letter")
                elif ev.typed[:2] == ev.correct[:2][::-1] and len(ev.correct) >= 2:
                    kinds.add("swapped letters")
                elif len(ev.typed) == len(ev.correct) and ev.typed[0] != ev.correct[0]:
                    kinds.add("neighbouring key")
        self.assertEqual(kinds, {"double letter", "swapped letters", "neighbouring key"})

    def test_backspaces_delete_only_what_the_mistake_added(self):
        for seed in range(15):
            steps = self.plan(seed=seed)
            pending = 0
            for s in steps:
                if s.kind == "char" and s.temp:
                    pending += 1
                elif s.kind == "backspace":
                    pending -= 1
                    self.assertGreaterEqual(pending, 0, "more Backspaces than mistake characters")
            self.assertEqual(pending, 0, "a mistake was left uncorrected")

    def test_mistakes_stay_inside_words_of_letters(self):
        text = "12345 67890 !!! ... --- \n\n ##### 1a2b3c ¿¿¿ 日本語 "
        steps = plan_steps(text, 60, STYLES["natural"], TypoConfig(True, 0.5), random.Random(1))
        self.assertEqual([s for s in steps if s.kind == "backspace"], [])      # nothing eligible
        steps = self.plan("hello world", seed=1, cfg=TypoConfig(True, 0.5, 0.5, 3))
        for s in steps:
            if s.kind == "char" and s.temp:
                self.assertTrue(s.ch.isalpha() and s.ch.isascii(), s.ch)       # only plain letters are typed wrongly

    def test_no_typos_when_disabled_or_rate_zero(self):
        for cfg in (TypoConfig(False, 0.5), TypoConfig(True, 0.0), None):
            steps = plan_steps(PROSE, 60, STYLES["natural"], cfg, random.Random(1))
            self.assertEqual(len(steps), len(PROSE))
            self.assertTrue(all(s.kind == "char" and not s.temp for s in steps))

    def test_higher_rate_means_more_mistakes(self):
        def count(rate):
            return sum(1 for s in plan_steps(PROSE * 3, 300, STYLES["natural"],
                                             TypoConfig(True, rate), random.Random(8)) if s.kind == "backspace")
        self.assertLess(count(0.02), count(0.15))
        self.assertLess(count(0.15), count(0.5))

    def test_correction_delay_is_honoured_in_seconds(self):
        steps = self.plan(duration=1000, cfg=TypoConfig(True, 0.3, correction_delay=1.0))
        gaps = []
        for i, s in enumerate(steps):
            if s.kind == "backspace" and steps[i - 1].kind == "char":     # first Backspace of a correction
                gaps.append(s.at - steps[i - 1].at)
        self.assertGreater(len(gaps), 5)
        for g in gaps:
            self.assertTrue(0.69 <= g <= 1.31, g)                        # 1.0 s x random(0.7, 1.3)

    def test_correction_time_can_never_swallow_the_duration(self):
        steps = plan_steps(PROSE, 20, STYLES["natural"], TypoConfig(True, 0.5, correction_delay=10), random.Random(2))
        self.assertAlmostEqual(steps[-1].at, 20.0, places=9)
        self.assertTrue(all(b.at >= a.at for a, b in zip(steps, steps[1:])))
        pauses = [s.at - steps[i - 1].at for i, s in enumerate(steps) if s.kind == "backspace"
                  and steps[i - 1].kind == "char"]
        self.assertLessEqual(sum(pauses), 0.31 * 20 + 1e-6)

    def test_chosen_duration_and_progress_with_corrections(self):
        steps = self.plan(duration=120)
        self.assertAlmostEqual(steps[-1].at, 120.0, places=9)
        commits = [s.commit for s in steps]
        self.assertTrue(all(b >= a for a, b in zip(commits, commits[1:])), "progress went backwards")
        self.assertEqual(commits[-1], len(PROSE))

    def test_config_is_bounded_and_text_is_never_modified(self):
        cfg = TypoConfig(True, 9, -4, 99).bounded()
        self.assertEqual((cfg.rate, cfg.correction_delay, cfg.max_lookahead), (0.5, 0.0, 3))
        original = PROSE
        plan_steps(original, 60, STYLES["natural"], self.CFG, random.Random(1))
        self.assertEqual(original, PROSE)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            plan_steps("", 10)
        with self.assertRaises(ValueError):
            plan_steps("abc", 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
