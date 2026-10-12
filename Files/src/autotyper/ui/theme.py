"""Light and dark themes: a QPalette plus one stylesheet built from a color table."""

from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

LIGHT = dict(
    bg="#F3F4F8", surface="#FFFFFF", surface_alt="#F1F2F7", hover="#E8EAF2", input_bg="#FFFFFF",
    border="#E2E4EC", border_strong="#C9CDDA", text="#1A1C25", muted="#6A6F82",
    accent="#4F5BD5", accent_hover="#434EC0", danger="#D93F45", danger_bg="#FDECEC",
    danger_bg_hover="#FADADB", success="#1F9D63", warning="#C98512", warn_bg="#FFF6E5",
    progress_bg="#E3E5EE",
)
DARK = dict(
    bg="#101218", surface="#1A1D26", surface_alt="#232734", hover="#2C3142", input_bg="#151821",
    border="#2A2E3C", border_strong="#3D4357", text="#EDEFF6", muted="#9AA1B6",
    accent="#6C77F2", accent_hover="#7E88F5", danger="#F0636A", danger_bg="#3A1D22",
    danger_bg_hover="#4A2328", success="#3DC587", warning="#E5A33A", warn_bg="#33281A",
    progress_bg="#2A2E3C",
)
PALETTES = {"light": LIGHT, "dark": DARK}

_QSS = Template("""
QWidget#root { background: $bg; }
QWidget { color: $text; }
QToolTip { background: $surface; color: $text; border: 1px solid $border; padding: 4px 8px; }

QFrame[card="true"] { background: $surface; border: 1px solid $border; border-radius: 14px; }
QFrame[card="warn"] { background: $warn_bg; border: 1px solid $warning; border-radius: 14px; }
QFrame#sep { background: $border; border: none; min-height: 1px; max-height: 1px; }

QLabel#title { font-size: 20px; font-weight: 700; }
QLabel#h2 { font-size: 15px; font-weight: 600; }
QLabel#rowTitle { font-size: 14px; font-weight: 600; }
QLabel#statusTitle { font-size: 22px; font-weight: 700; }
QLabel#statValue { font-weight: 600; }
QLabel[muted="true"] { color: $muted; }

QPlainTextEdit#editor {
    background: $input_bg; border: 1px solid $border; border-radius: 12px;
    padding: 12px; font-size: 14px; selection-background-color: $accent; selection-color: #FFFFFF;
}
QPlainTextEdit#editor:focus { border: 1px solid $accent; }

QPushButton {
    background: $surface_alt; border: 1px solid $border; border-radius: 10px;
    padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: $hover; }
QPushButton:disabled { color: $muted; }
QPushButton#primary {
    background: $accent; border: 1px solid $accent; color: #FFFFFF; padding: 12px 20px; font-size: 15px;
}
QPushButton#primary:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton#primary:disabled { background: $border; border-color: $border; color: $muted; }
QPushButton#danger {
    background: $danger_bg; border: 1px solid $danger; color: $danger; padding: 12px 20px; font-size: 15px;
}
QPushButton#danger:hover { background: $danger_bg_hover; }
QPushButton#danger:disabled { background: $surface_alt; border: 1px solid $border; color: $muted; }
QPushButton[ghost="true"] { background: transparent; border: 1px solid transparent; padding: 6px 10px; color: $muted; }
QPushButton[ghost="true"]:hover { background: $hover; color: $text; }
QPushButton[iconbtn="true"] { background: transparent; border: 1px solid $border; padding: 8px; }
QPushButton[iconbtn="true"]:hover { background: $hover; }
QPushButton[tab="true"] { background: transparent; border: 1px solid transparent; border-radius: 10px;
    padding: 8px 16px; color: $muted; font-weight: 600; }
QPushButton[tab="true"]:hover { background: $hover; color: $text; }
QPushButton[tab="true"]:checked { background: $surface; border: 1px solid $border; color: $text; }
QPushButton[chip="true"] { padding: 8px 6px; font-weight: 600; }
QPushButton[chip="true"]:checked { background: $accent; border-color: $accent; color: #FFFFFF; }

QComboBox, QSpinBox {
    background: $input_bg; border: 1px solid $border; border-radius: 8px; padding: 6px 10px; min-height: 22px;
}
QComboBox:focus, QSpinBox:focus { border-color: $accent; }
QComboBox QAbstractItemView {
    background: $surface; border: 1px solid $border; selection-background-color: $accent;
    selection-color: #FFFFFF; outline: 0; padding: 4px;
}

QProgressBar { background: $progress_bg; border: none; border-radius: 5px; min-height: 10px; max-height: 10px; }
QProgressBar::chunk { background: $accent; border-radius: 5px; }

QSlider::groove:horizontal { height: 6px; background: $progress_bg; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #FFFFFF; border: 2px solid $accent; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
}

QScrollArea { background: transparent; border: none; }
QWidget#scrollContent { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border_strong; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $border_strong; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
""")


def build_stylesheet(p):
    return _QSS.substitute(p)


def build_palette(p):
    pal = QPalette()
    R = QPalette.ColorRole
    pairs = {
        R.Window: p["bg"], R.WindowText: p["text"], R.Base: p["input_bg"],
        R.AlternateBase: p["surface_alt"], R.Text: p["text"], R.Button: p["surface_alt"],
        R.ButtonText: p["text"], R.ToolTipBase: p["surface"], R.ToolTipText: p["text"],
        R.Highlight: p["accent"], R.HighlightedText: "#FFFFFF", R.PlaceholderText: p["muted"],
        R.Mid: p["border_strong"], R.Link: p["accent"],
    }
    for role, color in pairs.items():
        pal.setColor(role, QColor(color))
    for role in (R.WindowText, R.Text, R.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(p["muted"]))
    return pal


def system_is_dark(app):
    hints = app.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    if scheme is not None:
        return scheme() == Qt.ColorScheme.Dark
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def resolve_theme(setting, system_dark):
    """'system' follows the OS; anything unknown falls back to light."""
    if setting == "dark":
        return "dark"
    if setting == "light":
        return "light"
    return "dark" if system_dark else "light"


def apply_theme(app, name):
    p = PALETTES[name]
    app.setPalette(build_palette(p))
    app.setStyleSheet(build_stylesheet(p))
    return p
