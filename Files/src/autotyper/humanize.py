"""
Humanized typing rhythm.

A HumanProfile describes how uneven the keystrokes are, how long the pauses around
words / punctuation / sentences / paragraphs are, and how often a longer "thinking"
pause happens. Everything is bounded, so no delay can become absurdly short or long.
"""

import random
from dataclasses import dataclass

MAX_JITTER = 0.9          # per-character delay factor stays within [1 - j, 1 + j]
MAX_PAUSE = 10.0          # pause multipliers are capped
MAX_THINK_CHANCE = 0.2    # at most 1 in 5 characters can start a thinking pause
MAX_THINK = 12.0          # a thinking pause is at most 12x a normal delay


def _clamp(value, low, high):
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class HumanProfile:
    jitter: float = 0.45           # random spread of each keystroke delay (0 = perfectly even)
    word_pause: float = 1.15       # multiplier for the delay after a space
    punct_pause: float = 1.8       # after  , ; :
    sentence_pause: float = 2.5    # after  . ! ?
    paragraph_pause: float = 3.0   # after a line break
    think_chance: float = 0.015    # probability per character of a longer thinking pause
    think_min: float = 3.0         # thinking pause = normal delay x random(think_min, think_max)
    think_max: float = 6.0

    def bounded(self):
        think_min = _clamp(self.think_min, 1.0, MAX_THINK)
        return HumanProfile(
            jitter=_clamp(self.jitter, 0.0, MAX_JITTER),
            word_pause=_clamp(self.word_pause, 1.0, MAX_PAUSE),
            punct_pause=_clamp(self.punct_pause, 1.0, MAX_PAUSE),
            sentence_pause=_clamp(self.sentence_pause, 1.0, MAX_PAUSE),
            paragraph_pause=_clamp(self.paragraph_pause, 1.0, MAX_PAUSE),
            think_chance=_clamp(self.think_chance, 0.0, MAX_THINK_CHANCE),
            think_min=think_min,
            think_max=_clamp(self.think_max, think_min, MAX_THINK),
        )

    @classmethod
    def from_variation(cls, variation):
        """Single 0..1 knob (used by the original API): 0 = even rhythm, 1 = Natural."""
        v = _clamp(variation, 0.0, 1.0)
        base = cls()
        return cls(
            jitter=base.jitter * v,
            word_pause=1.0 + (base.word_pause - 1.0) * v,
            punct_pause=1.0 + (base.punct_pause - 1.0) * v,
            sentence_pause=1.0 + (base.sentence_pause - 1.0) * v,
            paragraph_pause=1.0 + (base.paragraph_pause - 1.0) * v,
            think_chance=base.think_chance * v,
        )


FLAT = HumanProfile(jitter=0.0, word_pause=1.0, punct_pause=1.0, sentence_pause=1.0,
                    paragraph_pause=1.0, think_chance=0.0)

STYLES = {
    "steady": HumanProfile(jitter=0.12, word_pause=1.05, punct_pause=1.25, sentence_pause=1.4,
                           paragraph_pause=1.6, think_chance=0.0),
    "natural": HumanProfile(),
    "thoughtful": HumanProfile(jitter=0.6, word_pause=1.4, punct_pause=2.4, sentence_pause=3.6,
                               paragraph_pause=5.0, think_chance=0.04, think_min=4.0, think_max=9.0),
}
LEVELS = {"low": 0.5, "medium": 1.0, "high": 1.5}


def scaled(profile, k):
    """Make a profile weaker (k < 1) or stronger (k > 1); the result is always bounded."""
    return HumanProfile(
        jitter=profile.jitter * k,
        word_pause=1.0 + (profile.word_pause - 1.0) * k,
        punct_pause=1.0 + (profile.punct_pause - 1.0) * k,
        sentence_pause=1.0 + (profile.sentence_pause - 1.0) * k,
        paragraph_pause=1.0 + (profile.paragraph_pause - 1.0) * k,
        think_chance=profile.think_chance * k,
        think_min=profile.think_min,
        think_max=profile.think_max,
    ).bounded()


def build_profile(enabled=True, style="natural", level="medium",
                  variation=70, pauses=50, thinking=30):
    """Profile for the chosen settings.

    enabled=False       -> perfectly steady speed
    style               -> steady | natural | thoughtful (shape of the rhythm)
    level               -> low | medium | high (strength) or custom
    custom sliders (0-100): variation = keystroke spread, pauses = word/sentence/paragraph
    pauses (50 = the style's own), thinking = chance of thinking pauses (0-5 %)
    """
    if not enabled:
        return FLAT
    base = STYLES.get(style, STYLES["natural"])
    if level == "custom":
        v = _clamp(variation, 0, 100) / 100.0
        p = _clamp(pauses, 0, 100) / 50.0
        t = _clamp(thinking, 0, 100) / 100.0
        return HumanProfile(
            jitter=MAX_JITTER * v,
            word_pause=1.0 + (base.word_pause - 1.0) * p,
            punct_pause=1.0 + (base.punct_pause - 1.0) * p,
            sentence_pause=1.0 + (base.sentence_pause - 1.0) * p,
            paragraph_pause=1.0 + (base.paragraph_pause - 1.0) * p,
            think_chance=0.05 * t,
            think_min=max(base.think_min, 3.0),
            think_max=max(base.think_max, 6.0),
        ).bounded()
    return scaled(base, LEVELS.get(level, 1.0))


def pause_multiplier(ch, profile):
    if ch == " ":
        return profile.word_pause
    if ch in ",;:":
        return profile.punct_pause
    if ch in ".!?":
        return profile.sentence_pause
    if ch == "\n":
        return profile.paragraph_pause
    return 1.0


def char_weight(ch, profile, rng=None):
    """Relative delay before typing `ch` (1.0 = the average keystroke)."""
    rng = rng or random
    w = rng.uniform(1.0 - profile.jitter, 1.0 + profile.jitter)
    w *= pause_multiplier(ch, profile)
    if profile.think_chance > 0 and rng.random() < profile.think_chance:
        w *= rng.uniform(profile.think_min, profile.think_max)
    return w
