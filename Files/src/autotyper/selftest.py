"""
`AutoTyper --self-test`: verifies that a built (frozen) app really contains everything it
needs - Qt libraries, platform plugin, icons, backend - then exits 0 (ok) or 1 (problem).
Used by the installer build scripts. Details are written to a log file in the temp folder.
"""

import importlib
import os
import sys
import tempfile
import traceback

LOG = os.path.join(tempfile.gettempdir(), "AutoTyper-selftest.log")


def _check(name, fn, problems, log):
    try:
        fn()
        log.append(f"ok    {name}")
    except Exception:
        problems.append(name)
        log.append(f"FAIL  {name}\n{traceback.format_exc()}")


def gui_check():
    """Launch the real window in this (packaged) app and run two short typing sessions
    against a fake keyboard: one complete run with simulated typos, and one that is stopped."""
    import time

    from PySide6.QtWidgets import QApplication

    from .i18n import Translator
    from .settings import Settings
    from .system.base import InputBackend
    from .ui.main_window import MainWindow
    from .engine import TypingSession

    class FakeKeyboard(InputBackend):
        name = "selftest"

        def __init__(self):
            self.buf = ""

        def send_char(self, ch):
            self.buf += ch

        def send_backspace(self):
            self.buf = self.buf[:-1]

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    keyboard = FakeKeyboard()
    window = MainWindow(Settings(theme="light", typos=True, typo_rate=30, typo_delay=3), keyboard,
                        Translator("en"), lang="en", countdown=0, resume_countdown=0)
    window._is_qt_active = lambda: False   # nothing is in front of anything during the test

    def wait(condition, seconds):
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    text = "The quick brown fox jumps over the lazy dog. "
    window.editor.setPlainText(text)
    window.picker.set_value("custom", 3)
    window._on_start()
    if not wait(lambda: window.session is not None and not window.session.is_running, 15):
        raise RuntimeError("typing did not finish")
    if window.session.state != TypingSession.DONE or keyboard.buf != text:
        raise RuntimeError(f"typing result is wrong: {window.session.state} {keyboard.buf!r}")

    keyboard.buf = ""
    window.editor.setPlainText("a" * 300)
    window.picker.set_value("custom", 20)
    window._on_start()
    if not wait(lambda: len(keyboard.buf) > 3, 8):
        raise RuntimeError("second session did not start typing")
    window._on_stop()
    if not wait(lambda: not window.session.is_running, 2):
        raise RuntimeError("Stop did not stop the typing")
    typed = len(keyboard.buf)
    wait(lambda: False, 0.3)
    if window.session.state != TypingSession.STOPPED or len(keyboard.buf) != typed:
        raise RuntimeError("characters were typed after Stop")
    window.close()


def run_self_test():
    problems, log = [], []

    def qt_modules():
        for mod in ("PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvg"):
            importlib.import_module(mod)

    def app_modules():
        for mod in ("autotyper.engine", "autotyper.settings", "autotyper.i18n", "autotyper.system",
                    "autotyper.system.windows", "autotyper.system.macos", "autotyper.app",
                    "autotyper.ui.main_window", "autotyper.ui.settings_page",
                    "autotyper.ui.permission_panel", "autotyper.ui.widgets", "autotyper.ui.theme",
                    "autotyper.ui.icons", "autotyper.ui.humanize_page", "autotyper.ui.corrections_page",
                    "autotyper.humanize", "autotyper.plan"):
            importlib.import_module(mod)

    def platform_plugin():
        from PySide6.QtCore import QLibraryInfo
        plugins = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
        platforms = os.path.join(plugins, "platforms")
        wanted = "qwindows" if sys.platform == "win32" else "qcocoa" if sys.platform == "darwin" else "q"
        found = [f for f in os.listdir(platforms) if f.startswith(wanted)]
        if not found:
            raise FileNotFoundError(f"no {wanted} platform plugin in {platforms}")

    def resources():
        from .resources import resource_path
        icon = resource_path("assets", "icons", "icon.png")
        if not icon.exists():
            raise FileNotFoundError(str(icon))

    def icons():
        from .ui.icons import BODIES, render_image
        for name in BODIES:
            if render_image(name, "#000000", 20).isNull():
                raise RuntimeError(f"icon {name} did not render")

    def backend():
        from .system import backend_class, create_backend, platform_key
        expected = {"windows": "WindowsBackend", "macos": "MacBackend"}.get(platform_key(), "UnsupportedBackend")
        be = create_backend()
        if type(be).__name__ != expected or backend_class().__name__ != expected:
            raise RuntimeError(f"wrong backend {type(be).__name__} (expected {expected})")
        if "F8" not in be.available_stop_keys():
            raise RuntimeError("F8 is not available as stop key")

    def settings_roundtrip():
        from .settings import Settings, load_settings
        path = os.path.join(tempfile.gettempdir(), "AutoTyper-selftest-settings.json")
        Settings(variation=33).save(path)
        if load_settings(path).variation != 33:
            raise RuntimeError("settings round-trip failed")
        os.remove(path)

    checks = [("qt modules", qt_modules), ("app modules", app_modules),
              ("qt platform plugin", platform_plugin), ("resources", resources),
              ("icons", icons), ("keyboard backend", backend), ("settings", settings_roundtrip)]
    if os.environ.get("AUTOTYPER_SELFTEST_NOGUI") != "1":
        # starts the real window and types into a FAKE keyboard (never into a real app)
        checks.append(("window starts and types (with typos), Stop works", gui_check))
    for name, fn in checks:
        _check(name, fn, problems, log)

    log.append("RESULT: " + ("PASS" if not problems else "FAIL (" + ", ".join(problems) + ")"))
    try:
        with open(LOG, "w", encoding="utf-8") as fh:
            fh.write("\n".join(log))
    except OSError:
        pass
    return 0 if not problems else 1
