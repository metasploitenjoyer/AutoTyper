"""
Turns text into a timed list of keyboard steps (the "typing plan").

* Every character gets a humanized delay (see humanize.py).
* Optionally, simulated typos are planned. A typo never changes the original text:
  it types a wrong letter (plus up to a few following letters of the SAME word), waits,
  backspaces exactly the characters that belong to the mistake, and types the right ones.
  After the correction the destination contains exactly the original text.
* All steps are scaled so the last one lands on the chosen duration (the correction
  delay is honoured in real seconds as long as it stays under 30 % of the total).
"""

import random
import re
from dataclasses import dataclass

from .humanize import HumanProfile, char_weight

MAX_FIXED_SHARE = 0.30  # corrections may take at most this share of the total time


@dataclass(frozen=True)
class Step:
    at: float            # seconds after typing starts
    kind: str            # "char" or "backspace"
    ch: str = ""         # the character (kind == "char")
    commit: int = 0      # how many ORIGINAL characters are correctly in place after this step
    temp: bool = False   # True for characters that belong to a simulated mistake


@dataclass(frozen=True)
class TypoConfig:
    enabled: bool = False
    rate: float = 0.04             # share of words that get a mistake (0 .. 0.5)
    correction_delay: float = 0.8  # seconds before the "typist" notices and fixes it
    max_lookahead: int = 2         # letters typed after the mistake before noticing (0 .. 3)

    def bounded(self):
        return TypoConfig(
            enabled=bool(self.enabled),
            rate=max(0.0, min(0.5, float(self.rate))),
            correction_delay=max(0.0, min(10.0, float(self.correction_delay))),
            max_lookahead=max(0, min(3, int(self.max_lookahead))),
        )


@dataclass(frozen=True)
class _TypoEvent:
    typed: str     # what is typed for this stretch of the word (contains the mistake)
    correct: str   # what the original text has there


_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def _build_neighbors():
    pos = {ch: (r, c) for r, row in enumerate(_ROWS) for c, ch in enumerate(row)}
    return {ch: [o for o, (r2, c2) in pos.items() if o != ch and abs(r - r2) <= 1 and abs(c - c2) <= 1]
            for ch, (r, c) in pos.items()}


NEIGHBORS = _build_neighbors()
_WORD = re.compile(r"[A-Za-z]{3,}")


def _common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _plan_typos(text, cfg, rng):
    """Pick the words that get a mistake: {start index in text: _TypoEvent}."""
    events = {}
    for match in _WORD.finditer(text):
        if rng.random() >= cfg.rate:
            continue
        word, start = match.group(), match.start()
        kind = rng.choices(("sub", "swap", "dup"), weights=(0.6, 0.25, 0.15))[0]
        n = len(word)
        if kind == "swap":
            j = rng.randint(0, n - 2)
            room = n - 2 - j
        else:
            j = rng.randint(0, n - 1)
            room = n - 1 - j
        k = rng.randint(0, min(cfg.max_lookahead, room))  # letters typed before noticing
        if kind == "sub":
            neighbors = NEIGHBORS.get(word[j].lower())
            if not neighbors:
                continue
            wrong = rng.choice(neighbors)
            wrong = wrong.upper() if word[j].isupper() else wrong
            correct = word[j:j + 1 + k]
            typed = wrong + word[j + 1:j + 1 + k]
        elif kind == "swap":
            a, b = word[j], word[j + 1]
            if a.lower() == b.lower():
                continue
            correct = word[j:j + 2 + k]
            typed = b + a + word[j + 2:j + 2 + k]
        else:  # dup: the key is hit twice
            correct = word[j:j + 1 + k]
            typed = word[j] + correct
        if typed != correct:
            events[start + j] = _TypoEvent(typed, correct)
    return events


def plan_steps(text, total_seconds, profile=None, typos=None, rng=None):
    """Timed keyboard steps that type `text` in `total_seconds` (see module docstring)."""
    if not text:
        raise ValueError("text is empty")
    if total_seconds <= 0:
        raise ValueError("duration must be greater than zero")
    rng = rng or random
    profile = (profile or HumanProfile()).bounded()
    cfg = (typos or TypoConfig()).bounded()

    weights = [char_weight(ch, profile, rng) for ch in text]
    events = _plan_typos(text, cfg, rng) if cfg.enabled and cfg.rate > 0 else {}

    raw = []  # (kind, char, commit, temp, relative gap, fixed gap in seconds)
    i, n = 0, len(text)
    while i < n:
        ev = events.get(i)
        if ev is None:
            raw.append(("char", text[i], i + 1, False, weights[i], 0.0))
            i += 1
            continue
        typed, correct = ev.typed, ev.correct
        m = len(correct)
        cp = _common_prefix(typed, correct)       # leading characters that are already right
        for k, ch in enumerate(typed):
            w = weights[i + k] if k < m else weights[i + m - 1] * 0.8
            raw.append(("char", ch, i + min(k + 1, cp), k >= cp, w, 0.0))
        for b in range(len(typed) - cp):          # delete ONLY what belongs to the mistake
            if b == 0:
                raw.append(("backspace", "", i + cp, False, 0.0,
                            cfg.correction_delay * rng.uniform(0.7, 1.3)))
            else:
                raw.append(("backspace", "", i + cp, False, rng.uniform(0.35, 0.6), 0.0))
        for j in range(cp, m):
            w = rng.uniform(0.8, 1.4) if j == cp else weights[i + j]
            raw.append(("char", correct[j], i + j + 1, False, w, 0.0))
        i += m

    fixed_total = sum(r[5] for r in raw)
    cap = MAX_FIXED_SHARE * total_seconds
    fixed_scale = 1.0 if fixed_total <= cap else cap / fixed_total
    fixed_total *= fixed_scale
    weight_total = sum(r[4] for r in raw)
    weight_scale = (total_seconds - fixed_total) / weight_total

    steps, at = [], 0.0
    for kind, ch, commit, temp, gap_w, gap_f in raw:
        at += gap_w * weight_scale + gap_f * fixed_scale
        steps.append(Step(at, kind, ch, commit, temp))
    steps[-1] = Step(float(total_seconds), steps[-1].kind, steps[-1].ch, steps[-1].commit, steps[-1].temp)
    return steps


def build_schedule(text, total_seconds, rng=None, variation=1.0):
    """Time (seconds after the start) at which each character is typed, without typos.

    variation: 0 = perfectly even rhythm, 1 = natural. The last character lands exactly
    at total_seconds.
    """
    steps = plan_steps(text, total_seconds, HumanProfile.from_variation(variation), None, rng)
    return [s.at for s in steps]
