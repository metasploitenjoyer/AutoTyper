"""Settings persistence, per-OS config folders and translations."""

import json
import os
import re
import tempfile
import unittest

import _path  # noqa: F401
from autotyper.i18n import EN, ES, Translator, detect_language, fmt_int
from autotyper.settings import (PRESETS, Settings, config_dir, default_settings_path, distinct_keys,
                                load_settings)

UI_DIR = os.path.join(_path.SRC, "autotyper")


class SettingsTests(unittest.TestCase):
    def test_defaults_match_the_spec(self):
        s = Settings()
        self.assertEqual(s.stop_key, "F8")
        self.assertEqual(s.duration_seconds(), 60)
        self.assertEqual(s.theme, "system")
        self.assertFalse(s.always_on_top)

    def test_duration_presets_and_custom(self):
        self.assertEqual(PRESETS, {"30s": 30, "1m": 60, "2m": 120, "5m": 300, "10m": 600})
        for key, secs in PRESETS.items():
            self.assertEqual(Settings(duration_preset=key).duration_seconds(), secs)
        self.assertEqual(Settings(duration_preset="custom", custom_seconds=217).duration_seconds(), 217)

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "settings.json")
            original = Settings("custom", 95, 40, "F7", "dark", True, "es", humanize=False,
                                human_style="thoughtful", human_level="custom", custom_pauses=80,
                                custom_thinking=10, typos=True, typo_rate=12, typo_delay=20,
                                pause_key="F10", stop_on_focus_change=False)
            original.save(path)
            self.assertEqual(load_settings(path), original)

    def test_missing_or_corrupt_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_settings(os.path.join(tmp, "nope.json")), Settings())
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w") as fh:
                fh.write("{ not json")
            self.assertEqual(load_settings(bad), Settings())
            with open(bad, "w") as fh:
                json.dump(["a", "list"], fh)
            self.assertEqual(load_settings(bad), Settings())

    def test_invalid_values_are_repaired(self):
        s = Settings.from_dict({"variation": 900, "theme": "neon", "duration_preset": "7m",
                                "custom_seconds": -4, "language": "xx", "stop_key": 5})
        self.assertEqual((s.variation, s.theme, s.duration_preset, s.language, s.stop_key),
                         (100, "system", "1m", "auto", "F8"))
        self.assertGreaterEqual(s.custom_seconds, 1)

    def test_stop_key_must_exist_on_this_platform(self):
        mac_keys = ["F1", "F8", "Esc"]
        self.assertEqual(Settings.from_dict({"stop_key": "Pause"}, mac_keys).stop_key, "F8")
        self.assertEqual(Settings.from_dict({"stop_key": "Esc"}, mac_keys).stop_key, "Esc")

    def test_new_options_have_safe_defaults(self):
        s = Settings()
        self.assertTrue(s.humanize)
        self.assertEqual((s.human_style, s.human_level), ("natural", "medium"))
        self.assertFalse(s.typos)                     # simulated typos are opt-in
        self.assertTrue(s.stop_on_focus_change)       # safety on by default
        self.assertEqual((s.stop_key, s.pause_key), ("F8", "F9"))

    def test_invalid_new_options_are_repaired(self):
        s = Settings.from_dict({"humanize": 0, "human_style": "wild", "human_level": "extreme",
                                "custom_pauses": 500, "custom_thinking": -9, "typo_rate": 0,
                                "typo_delay": 999, "pause_key": "Nope", "stop_on_focus_change": "yes"},
                               ["F8", "F9", "Esc"])   # the platform's real key list, as the app passes it
        self.assertEqual((s.humanize, s.human_style, s.human_level), (False, "natural", "medium"))
        self.assertEqual((s.custom_pauses, s.custom_thinking), (100, 0))
        self.assertEqual((s.typo_rate, s.typo_delay), (1, 50))   # clamped into the allowed range
        self.assertEqual(s.pause_key, "F9")
        self.assertIs(s.stop_on_focus_change, True)

    def test_stop_and_pause_keys_can_never_be_the_same(self):
        s = Settings.from_dict({"stop_key": "F9", "pause_key": "F9"})
        self.assertNotEqual(s.stop_key, s.pause_key)
        s = Settings.from_dict({"stop_key": "F8", "pause_key": "F8"}, ["F8", "F9", "Esc"])
        self.assertEqual((s.stop_key, s.pause_key), ("F8", "F9"))
        self.assertEqual(distinct_keys("F8", "F9"), "F9")
        self.assertEqual(distinct_keys("F9", "F9"), "F10")

    def test_config_folder_differs_per_os(self):
        home = os.path.join(os.sep, "home", "ana")
        win = config_dir("win32", env={"APPDATA": os.path.join(os.sep, "AppData")}, home=home)
        mac = config_dir("darwin", env={}, home=home)
        lin = config_dir("linux", env={}, home=home)
        self.assertTrue(win.startswith(os.path.join(os.sep, "AppData")))
        self.assertIn(os.path.join("Library", "Application Support", "AutoTyper"), mac)
        self.assertIn(os.path.join(".config", "AutoTyper"), lin)
        self.assertTrue(default_settings_path(platform="darwin", env={}, home=home).endswith("settings.json"))


class TranslationTests(unittest.TestCase):
    def test_both_languages_have_the_same_keys_and_placeholders(self):
        self.assertEqual(set(EN), set(ES))
        for key in EN:
            self.assertEqual(sorted(re.findall(r"{(\w+)}", EN[key])),
                             sorted(re.findall(r"{(\w+)}", ES[key])), key)

    def test_every_key_used_in_the_code_exists(self):
        used = set()
        for folder, _dirs, files in os.walk(UI_DIR):
            for name in files:
                if name.endswith(".py") and name != "i18n.py":
                    with open(os.path.join(folder, name), encoding="utf-8") as fh:
                        used |= set(re.findall(r"\bt\(\s*\"([a-z0-9_]+)\"\s*[,)]", fh.read()))
        # keys built dynamically: dur_<preset>, theme_<name>, lang_<code>
        for prefix, names in (("dur_", ["30s", "1m", "2m", "5m", "10m", "custom"]),
                              ("theme_", ["system", "light", "dark"]), ("lang_", ["auto", "es", "en"]),
                              ("style_", ["steady", "natural", "thoughtful"]),
                              ("style_", ["steady_help", "natural_help", "thoughtful_help"]),
                              ("level_", ["low", "medium", "high", "custom"])):
            used |= {prefix + n for n in names}
        self.assertGreater(len(used), 40)
        self.assertEqual(sorted(k for k in used if k not in EN), [])

    def test_buttons_are_called_start_and_stop_in_both_languages(self):
        for table in (EN, ES):
            self.assertEqual((table["start"], table["stop"]), ("Start", "Stop"))

    def test_translator(self):
        self.assertEqual(Translator("es")("stop_hint", key="F8"), "Pulsa F8 para detener al instante")
        self.assertEqual(Translator("en")("stop_hint", key="F8"), "Press F8 to stop instantly")
        self.assertEqual(Translator("zz")("start"), "Start")          # unknown language -> English
        self.assertEqual(Translator("en")("missing_key"), "missing_key")

    def test_language_detection_and_number_format(self):
        self.assertEqual(detect_language("es_CO"), "es")
        self.assertEqual(detect_language("es"), "es")
        self.assertEqual(detect_language("en_US"), "en")
        self.assertEqual(detect_language(None), "en")
        self.assertEqual(fmt_int(2000, "en"), "2,000")
        self.assertEqual(fmt_int(2000, "es"), "2.000")


if __name__ == "__main__":
    unittest.main(verbosity=2)
