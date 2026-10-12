"""User settings stored as JSON in the per-user application-data folder."""

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass

from . import APP_NAME
from .system.base import DEFAULT_STOP_KEY

PRESETS = {"30s": 30, "1m": 60, "2m": 120, "5m": 300, "10m": 600}
PRESET_ORDER = ["30s", "1m", "2m", "5m", "10m", "custom"]
THEMES = ("system", "light", "dark")
LANGUAGES = ("auto", "es", "en")
HUMAN_STYLES = ("steady", "natural", "thoughtful")
HUMAN_LEVELS = ("low", "medium", "high", "custom")
DEFAULT_PAUSE_KEY = "F9"


def config_dir(platform=None, env=None, home=None):
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = home or os.path.expanduser("~")
    if platform.startswith("win"):
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, APP_NAME)


def default_settings_path(**kwargs):
    return os.path.join(config_dir(**kwargs), "settings.json")


def _clamp(value, low, high, default):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def distinct_keys(stop_key, pause_key, valid_keys=None):
    """The stop and pause shortcuts must be different keys."""
    if pause_key != stop_key:
        return pause_key
    for candidate in (DEFAULT_PAUSE_KEY, "F10", "F7", "F6"):
        if candidate != stop_key and (valid_keys is None or candidate in valid_keys):
            return candidate
    return pause_key


@dataclass
class Settings:
    duration_preset: str = "1m"
    custom_seconds: int = 180
    variation: int = 70            # Humanization > Custom: keystroke variation, 0..100 (%)
    stop_key: str = DEFAULT_STOP_KEY
    theme: str = "system"
    always_on_top: bool = False
    language: str = "auto"
    # Humanization
    humanize: bool = True
    human_style: str = "natural"   # steady | natural | thoughtful
    human_level: str = "medium"    # low | medium | high | custom
    custom_pauses: int = 50        # Custom: word / sentence / paragraph pauses, 0..100 (50 = style default)
    custom_thinking: int = 30      # Custom: thinking pauses, 0..100
    # Corrections
    typos: bool = False
    typo_rate: int = 4             # % of words that get a simulated mistake, 1..30
    typo_delay: int = 8            # correction delay in tenths of a second, 3..50
    # Safety / shortcuts
    pause_key: str = DEFAULT_PAUSE_KEY
    stop_on_focus_change: bool = True

    def duration_seconds(self):
        return PRESETS.get(self.duration_preset) or max(1, self.custom_seconds)

    @classmethod
    def from_dict(cls, data, valid_stop_keys=None):
        d = cls()
        if not isinstance(data, dict):
            return d
        preset = data.get("duration_preset")
        d.duration_preset = preset if preset in PRESET_ORDER else d.duration_preset
        d.custom_seconds = _clamp(data.get("custom_seconds"), 1, 36000, d.custom_seconds)
        d.variation = _clamp(data.get("variation"), 0, 100, d.variation)
        key = data.get("stop_key")
        if isinstance(key, str) and (valid_stop_keys is None or key in valid_stop_keys):
            d.stop_key = key
        theme = data.get("theme")
        d.theme = theme if theme in THEMES else d.theme
        d.always_on_top = bool(data.get("always_on_top", d.always_on_top))
        lang = data.get("language")
        d.language = lang if lang in LANGUAGES else d.language

        d.humanize = bool(data.get("humanize", d.humanize))
        style = data.get("human_style")
        d.human_style = style if style in HUMAN_STYLES else d.human_style
        level = data.get("human_level")
        d.human_level = level if level in HUMAN_LEVELS else d.human_level
        d.custom_pauses = _clamp(data.get("custom_pauses"), 0, 100, d.custom_pauses)
        d.custom_thinking = _clamp(data.get("custom_thinking"), 0, 100, d.custom_thinking)
        d.typos = bool(data.get("typos", d.typos))
        d.typo_rate = _clamp(data.get("typo_rate"), 1, 30, d.typo_rate)
        d.typo_delay = _clamp(data.get("typo_delay"), 3, 50, d.typo_delay)
        pause = data.get("pause_key")
        if isinstance(pause, str) and (valid_stop_keys is None or pause in valid_stop_keys):
            d.pause_key = pause
        d.pause_key = distinct_keys(d.stop_key, d.pause_key, valid_stop_keys)
        d.stop_on_focus_change = bool(data.get("stop_on_focus_change", d.stop_on_focus_change))
        return d

    def save(self, path):
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(asdict(self), fh, indent=2)
            os.replace(tmp, path)  # atomic: never leaves a half-written file
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


def load_settings(path, valid_stop_keys=None):
    """Load settings; a missing or corrupt file simply gives the defaults."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return Settings.from_dict(json.load(fh), valid_stop_keys)
    except (OSError, ValueError):
        return Settings()
