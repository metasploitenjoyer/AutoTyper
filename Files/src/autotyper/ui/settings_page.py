"""The Settings page: duration, speed variation, stop shortcut, theme, always-on-top, language."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .widgets import Card, DurationPicker, Switch, make_label

THEME_KEYS = ("system", "light", "dark")
LANG_KEYS = ("auto", "es", "en")


class SettingsPage(QWidget):
    duration_changed = Signal()
    stop_key_changed = Signal(str)
    pause_key_changed = Signal(str)
    focus_guard_changed = Signal(bool)
    theme_changed = Signal(str)
    on_top_changed = Signal(bool)
    language_changed = Signal(str)
    open_accessibility = Signal()
    open_input_monitoring = Signal()
    check_permissions = Signal()

    def __init__(self, t, backend, parent=None):
        super().__init__(parent)
        self.t = t
        self.icon_targets = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("scrollContent")
        col = QVBoxLayout(content)
        col.setContentsMargins(0, 0, 6, 0)
        col.setSpacing(14)

        card = Card()
        # duration
        self.duration_picker = DurationPicker(t)
        card.body.addWidget(make_label(t("set_duration"), "rowTitle"))
        card.body.addWidget(make_label(t("set_duration_help"), muted=True, wrap=True))
        card.body.addWidget(self.duration_picker)
        self.duration_picker.changed.connect(self.duration_changed)
        card.body.addWidget(self._separator())

        # stop shortcut
        self.stop_combo = QComboBox()
        for key in backend.available_stop_keys():
            self.stop_combo.addItem(key, key)
        help_text = t("set_stop_help")
        card.body.addWidget(self._row(t("set_stop_key"), help_text, self.stop_combo))
        if backend.fn_key_hint:
            card.body.addWidget(make_label(t("set_stop_key_mac"), muted=True, wrap=True))
        self.stop_combo.currentIndexChanged.connect(
            lambda i: self.stop_key_changed.emit(self.stop_combo.itemData(i)))
        card.body.addWidget(self._separator())

        # pause shortcut
        self.pause_combo = QComboBox()
        for key in backend.available_stop_keys():
            self.pause_combo.addItem(key, key)
        card.body.addWidget(self._row(t("set_pause_key"), t("set_pause_help"), self.pause_combo))
        self.pause_combo.currentIndexChanged.connect(
            lambda i: self.pause_key_changed.emit(self.pause_combo.itemData(i)))
        card.body.addWidget(self._separator())

        # stop if the active window changes
        self.focus_switch = Switch()
        card.body.addWidget(self._row(t("set_focus"), t("set_focus_help"), self.focus_switch))
        self.focus_switch.toggled.connect(self.focus_guard_changed)
        card.body.addWidget(self._separator())

        # theme
        self.theme_combo = QComboBox()
        for key in THEME_KEYS:
            self.theme_combo.addItem(t("theme_" + key), key)
        card.body.addWidget(self._row(t("set_theme"), "", self.theme_combo))
        self.theme_combo.currentIndexChanged.connect(
            lambda i: self.theme_changed.emit(self.theme_combo.itemData(i)))
        card.body.addWidget(self._separator())

        # always on top
        self.top_switch = Switch()
        card.body.addWidget(self._row(t("set_on_top"), "", self.top_switch))
        self.top_switch.toggled.connect(self.on_top_changed)
        card.body.addWidget(self._separator())

        # language
        self.lang_combo = QComboBox()
        for key in LANG_KEYS:
            self.lang_combo.addItem(t("lang_" + key), key)
        card.body.addWidget(self._row(t("set_language"), t("lang_restart"), self.lang_combo))
        self.lang_combo.currentIndexChanged.connect(
            lambda i: self.language_changed.emit(self.lang_combo.itemData(i)))
        col.addWidget(card)

        # macOS permissions
        self.perm_card = None
        if backend.needs_permissions:
            self.perm_card = Card()
            self.perm_card.body.addWidget(make_label(t("set_perm_section"), "h2"))
            self.acc_status = make_label("")
            self.inp_status = make_label("")
            self.perm_card.body.addWidget(self._row(t("perm_accessibility"), "", self.acc_status))
            self.perm_card.body.addWidget(self._row(t("perm_input_monitoring"), "", self.inp_status))
            buttons = QHBoxLayout()
            buttons.setSpacing(8)
            b1 = QPushButton(t("perm_open"))
            b2 = QPushButton(t("perm_open_input"))
            b3 = QPushButton(t("perm_check"))
            for b in (b1, b2, b3):
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                buttons.addWidget(b)
            buttons.addStretch(1)
            self.perm_card.body.addLayout(buttons)
            b1.clicked.connect(self.open_accessibility)
            b2.clicked.connect(self.open_input_monitoring)
            b3.clicked.connect(self.check_permissions)
            col.addWidget(self.perm_card)

        col.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # ---- helpers -------------------------------------------------------
    def _separator(self):
        line = QFrame()
        line.setObjectName("sep")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _row(self, title, help_text, control):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(make_label(title, "rowTitle", wrap=True))
        if help_text:
            left.addWidget(make_label(help_text, muted=True, wrap=True))
        h.addLayout(left, 1)
        h.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row

    # ---- state -----------------------------------------------------------
    def load(self, settings):
        """Show the given settings without emitting change signals."""
        self.duration_picker.set_value(settings.duration_preset, settings.custom_seconds)
        for widget, setter in (
            (self.stop_combo, lambda: self.stop_combo.setCurrentIndex(
                max(0, self.stop_combo.findData(settings.stop_key)))),
            (self.pause_combo, lambda: self.pause_combo.setCurrentIndex(
                max(0, self.pause_combo.findData(settings.pause_key)))),
            (self.focus_switch, lambda: self.focus_switch.setChecked(settings.stop_on_focus_change)),
            (self.theme_combo, lambda: self.theme_combo.setCurrentIndex(
                max(0, self.theme_combo.findData(settings.theme)))),
            (self.top_switch, lambda: self.top_switch.setChecked(settings.always_on_top)),
            (self.lang_combo, lambda: self.lang_combo.setCurrentIndex(
                max(0, self.lang_combo.findData(settings.language)))),
        ):
            widget.blockSignals(True)
            setter()
            widget.blockSignals(False)

    def set_stop_keys(self, stop_key, pause_key):
        """Reflect corrected shortcuts (the two keys must differ) without emitting signals."""
        for combo, key in ((self.stop_combo, stop_key), (self.pause_combo, pause_key)):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(key)))
            combo.blockSignals(False)

    def set_theme(self, name):
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(name)))
        self.theme_combo.blockSignals(False)

    def set_permission_status(self, status):
        if self.perm_card is None:
            return
        t = self.t
        self.acc_status.setText(t("perm_granted") if status.accessibility else t("perm_not_granted"))
        self.inp_status.setText(t("perm_granted") if status.input_monitoring else t("perm_not_granted"))
