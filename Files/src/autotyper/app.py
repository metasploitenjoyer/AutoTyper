"""Application start-up: detects the OS, loads settings and shows the window."""

import sys

from . import APP_NAME
from .i18n import Translator, detect_language
from .resources import resource_path
from .settings import default_settings_path, load_settings
from .system import create_backend


def run(argv=None):
    from PySide6.QtCore import QLocale
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .ui.main_window import MainWindow

    backend = create_backend()          # Windows -> SendInput, macOS -> Quartz events
    backend.prepare_process()           # before any window exists (taskbar identity, timers)

    settings_path = default_settings_path()
    settings = load_settings(settings_path, backend.available_stop_keys())

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setStyle("Fusion")  # identical base look on every platform; our theme is layered on top
    icon_file = resource_path("assets", "icons", "icon.png")
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    lang = settings.language
    if lang == "auto":
        lang = detect_language(QLocale.system().name())

    window = MainWindow(settings, backend, Translator(lang), lang=lang, settings_path=settings_path)
    window.show()
    return app.exec()
