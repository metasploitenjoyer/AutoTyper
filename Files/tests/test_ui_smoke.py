"""
End-to-end tests of the real Qt window with a fake keyboard (no real keys are pressed).
They run headless (QT_QPA_PLATFORM=offscreen) and are skipped automatically when PySide6
is not installed. Install the dependencies and run:  python -m unittest discover -s tests -v
"""

import json
import os
import tempfile
import time
import unittest

import _path  # noqa: F401

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QBoxLayout
    HAS_QT = True
except Exception:  # PySide6 missing or unusable
    HAS_QT = False

from autotyper.engine import TypingSession
from autotyper.i18n import Translator
from autotyper.settings import Settings
from autotyper.system.base import InputBackend, PermissionStatus


class FakeBackend(InputBackend):
    name = "fake"

    def __init__(self):
        self.typed = []
        self.buf = ""
        self.stop_down = False
        self.requested = 0

    def send_char(self, ch):
        self.typed.append(ch)
        self.buf += ch

    def send_backspace(self):
        self.buf = self.buf[:-1]

    def is_stop_key_down(self, key_name):
        return self.stop_down


class FakeMacBackend(FakeBackend):
    needs_permissions = True
    fn_key_hint = True

    def __init__(self):
        super().__init__()
        self.status = PermissionStatus(False, False)

    def permissions(self):
        return self.status

    def request_permissions(self):
        self.requested += 1


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.windows = []

    def tearDown(self):
        for win in self.windows:
            if win.session:
                win.session.stop()
                win.session.join(2)
            win.close()
            win.deleteLater()

    # ---- helpers -------------------------------------------------------
    def make(self, backend=None, settings=None, countdown=0, path=None):
        from autotyper.ui.main_window import MainWindow
        backend = backend or FakeBackend()
        settings = settings or Settings(theme="light")
        win = MainWindow(settings, backend, Translator("en"), lang="en", settings_path=path,
                         countdown=countdown, resume_countdown=0)
        win._is_qt_active = lambda: False      # the offscreen "app" is always active
        self.windows.append(win)
        return win, backend

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def wait_for(self, condition, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def finished(self, win):
        return win.session is not None and not win.session.is_running

    # ---- tests ---------------------------------------------------------
    def test_initial_state(self):
        win, _ = self.make()
        win.show()
        self.pump(0.2)
        self.assertEqual(win.status_title.text(), "Ready")
        self.assertTrue(win.start_btn.isEnabled())
        self.assertFalse(win.stop_btn.isEnabled())
        self.assertEqual(win.start_btn.text(), "Start")
        self.assertEqual(win.stop_btn.text(), "Stop")
        self.assertIn("F8", win.stop_hint.text())

    def test_counter_and_speed(self):
        win, _ = self.make()
        win.picker.set_value("5m", 180)
        win.editor.setPlainText("x" * 1000)
        self.pump(0.1)
        self.assertIn("1,000 characters", win.count_label.text())
        self.assertIn("3.3 chars/sec", win.speed_label.text())   # 1,000 chars over 5 min
        self.assertIn("40 words/min", win.speed_label.text())
        self.assertTrue(win.speed_warn.isHidden())
        win.picker.set_value("30s", 180)
        win.editor.setPlainText("y" * 1000)                      # 33 chars/s -> too fast warning
        self.assertFalse(win.speed_warn.isHidden())

    def test_types_exact_text_and_shows_progress(self):
        win, backend = self.make()
        text = "Line one.\n\nLine two, café — ¿qué tal?\tEnd"
        win.editor.setPlainText(text)
        win.picker.set_value("custom", 1)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win)))
        self.pump(0.3)
        self.assertEqual("".join(backend.typed), text)
        self.assertEqual(win.session.state, TypingSession.DONE)
        self.assertEqual(win.bar.value(), 100)
        self.assertEqual(win.pct_value.text(), "100%")
        self.assertEqual(win.chars_value.text(), f"{len(text)} / {len(text)}")
        self.assertEqual(win.time_value.text(), "0:00")
        self.assertEqual(win.status_title.text(), "Done")

    def test_stop_button_stops_immediately(self):
        win, backend = self.make()
        win.editor.setPlainText("a" * 300)
        win.picker.set_value("custom", 20)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: len(backend.typed) > 3))
        win.stop_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=1.0))
        count = len(backend.typed)
        self.pump(0.4)
        self.assertEqual(len(backend.typed), count)              # nothing typed after Stop
        self.assertEqual(win.session.state, TypingSession.STOPPED)
        self.assertEqual(win.status_title.text(), "Stopped")
        self.assertTrue(win.start_btn.isEnabled())

    def test_stop_key_stops_immediately(self):
        win, backend = self.make()
        win.editor.setPlainText("a" * 300)
        win.picker.set_value("custom", 20)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: len(backend.typed) > 3))
        backend.stop_down = True                                  # the user presses F8
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=1.0))
        count = len(backend.typed)
        self.pump(0.3)
        self.assertEqual(len(backend.typed), count)
        self.assertEqual(win.session.state, TypingSession.STOPPED)

    def test_never_types_into_autotyper_itself(self):
        win, backend = self.make()
        win._is_qt_active = lambda: True                          # AutoTyper is the active window
        win.editor.setPlainText("hello")
        win.picker.set_value("custom", 2)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=2.0))
        self.pump(0.3)
        self.assertEqual(backend.typed, [])
        self.assertEqual(win.session.cause, "abort")
        self.assertIn("active window", win.status_hint.text())

    def test_countdown_then_stop_types_nothing(self):
        win, backend = self.make(countdown=5)
        win.editor.setPlainText("hello")
        win.start_btn.click()
        self.pump(0.4)
        self.assertIn("Starting in", win.status_title.text())
        win.stop_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=1.0))
        self.assertEqual(backend.typed, [])

    def test_empty_text_shows_a_notice_instead_of_starting(self):
        win, _ = self.make()
        win.start_btn.click()
        self.pump(0.2)
        self.assertIsNone(win.session)
        self.assertIn("Paste some text", win.status_hint.text())

    def test_theme_toggle_and_system_option(self):
        win, _ = self.make(settings=Settings(theme="light"))
        self.assertEqual(win._resolved, "light")
        win.theme_btn.click()
        self.assertEqual((win.settings.theme, win._resolved), ("dark", "dark"))
        self.assertIn("#101218", self.app.styleSheet())
        win.theme_btn.click()
        self.assertEqual(win._resolved, "light")
        self.assertIn("#F3F4F8", self.app.styleSheet())

    def test_layout_adapts_to_window_size(self):
        win, _ = self.make()
        win.show()
        win.resize(1100, 720)
        self.pump(0.2)
        self.assertEqual(win.body.direction(), QBoxLayout.Direction.LeftToRight)
        win.resize(560, 820)
        self.pump(0.2)
        self.assertEqual(win.body.direction(), QBoxLayout.Direction.TopToBottom)

    def test_tabs_and_settings_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            win, _ = self.make(path=path)
            self.assertEqual([b.text() for b in win.tab_buttons],
                             ["Typing", "Humanization", "Corrections", "Settings"])
            win.tab_buttons[3].click()
            self.assertEqual(win.stack.currentIndex(), 3)
            sp = win.settings_page
            sp.stop_combo.setCurrentIndex(sp.stop_combo.findData("F7"))
            sp.pause_combo.setCurrentIndex(sp.pause_combo.findData("F7"))   # same key as Stop: must be refused
            sp.top_switch.setChecked(True)
            sp.focus_switch.setChecked(False)
            sp.duration_picker._buttons["5m"].click()
            self.assertEqual(win.settings.stop_key, "F7")
            self.assertNotEqual(win.settings.pause_key, "F7")
            self.assertIn("F7", win.stop_hint.text())
            self.assertTrue(win.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            self.assertEqual(win.picker.preset(), "5m")             # both duration pickers stay in sync
            with open(path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertEqual((saved["stop_key"], saved["always_on_top"], saved["duration_preset"],
                              saved["stop_on_focus_change"]), ("F7", True, "5m", False))
            win.tab_buttons[0].click()
            self.assertEqual(win.stack.currentIndex(), 0)

    def test_humanization_and_corrections_tabs_save_their_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            win, _ = self.make(path=path)
            hp = win.human_page
            hp.style_chips._buttons["thoughtful"].click()
            hp.level_chips._buttons["custom"].click()
            self.assertFalse(hp.custom_box.isHidden())
            hp.var_slider.slider.setValue(33)
            tp = win.typo_page
            tp.enable_switch.setChecked(True)
            tp.rate_slider.slider.setValue(12)
            tp.delay_slider.slider.setValue(15)
            with open(path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertEqual((saved["human_style"], saved["human_level"], saved["variation"]),
                             ("thoughtful", "custom", 33))
            self.assertEqual((saved["typos"], saved["typo_rate"], saved["typo_delay"]), (True, 12, 15))
            hp.enable_switch.setChecked(False)
            self.assertFalse(hp.options.isEnabled())                # style/intensity are greyed out when off

    def test_corrections_end_to_end_leave_the_exact_text(self):
        win, backend = self.make(settings=Settings(theme="light", typos=True, typo_rate=30, typo_delay=3))
        text = "The quick brown fox jumps over the lazy dog. " * 3
        win.editor.setPlainText(text)
        win.picker.set_value("custom", 4)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=10))
        self.pump(0.3)
        self.assertEqual(backend.buf, text)
        self.assertEqual(win.editor.toPlainText(), text)            # the editor text is untouched
        self.assertEqual(win.session.state, TypingSession.DONE)

    def test_pause_and_resume_buttons(self):
        win, backend = self.make()
        win.editor.setPlainText("a" * 300)
        win.picker.set_value("custom", 20)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: len(backend.typed) > 3))
        win.pause_btn.click()
        self.assertTrue(self.wait_for(lambda: win.session.state == TypingSession.PAUSED, timeout=1.0))
        self.pump(0.2)
        self.assertEqual(win.pause_btn.text(), "Resume")
        self.assertEqual(win.status_title.text(), "Paused")
        count = len(backend.typed)
        self.pump(0.4)
        self.assertEqual(len(backend.typed), count)                 # nothing typed while paused
        win.pause_btn.click()                                       # Resume
        self.assertTrue(self.wait_for(lambda: len(backend.typed) > count))
        self.assertTrue(self.wait_for(lambda: win.pause_btn.text() == "Pause", timeout=2.0))  # label follows on the next refresh
        win.stop_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win), timeout=1.0))

    def test_elapsed_and_remaining_are_shown(self):
        win, backend = self.make()
        win.editor.setPlainText("a" * 200)
        win.picker.set_value("custom", 10)
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: win.session.elapsed() > 2.0))
        self.pump(0.3)                                              # let the 100 ms refresh run
        self.assertNotEqual(win.elapsed_value.text(), "0:00")
        self.assertNotEqual(win.time_value.text(), "0:10")          # remaining time has started to count down
        win.stop_btn.click()

    def test_mac_permission_banner_blocks_typing_until_granted(self):
        backend = FakeMacBackend()
        win, _ = self.make(backend=backend)
        self.assertFalse(win.perm_panel.isHidden())                 # instructions are shown
        win.editor.setPlainText("hello")
        win.picker.set_value("custom", 1)
        win.start_btn.click()
        self.pump(0.2)
        self.assertEqual(backend.requested, 1)                      # asked macOS for the permission
        self.assertIsNone(win.session)
        self.assertEqual(backend.typed, [])
        backend.status = PermissionStatus(True, True)               # user enabled it in System Settings
        win._update_permissions()
        self.assertTrue(win.perm_panel.isHidden())
        win.start_btn.click()
        self.assertTrue(self.wait_for(lambda: self.finished(win)))
        self.assertEqual("".join(backend.typed), "hello")


if __name__ == "__main__":
    unittest.main(verbosity=2)
