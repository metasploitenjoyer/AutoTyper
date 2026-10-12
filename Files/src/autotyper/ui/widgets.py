"""Reusable widgets: Card, Switch, DurationPicker and a label helper."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QSizePolicy, QSlider, QSpinBox, QVBoxLayout, QWidget)

from ..settings import PRESET_ORDER, PRESETS


def make_label(text="", name=None, muted=False, wrap=False):
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    if muted:
        label.setProperty("muted", "true")
    if wrap:
        label.setWordWrap(True)
    return label


class Card(QFrame):
    """Rounded surface with a vertical body layout (`card.body`)."""

    def __init__(self, kind="true", parent=None):
        super().__init__(parent)
        self.setProperty("card", kind)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(12)


class Switch(QAbstractButton):
    """Modern on/off toggle (colors come from the application palette)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)

    def sizeHint(self):
        return QSize(44, 24)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        role = QPalette.ColorRole.Highlight if self.isChecked() else QPalette.ColorRole.Mid
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pal.color(role))
        painter.drawRoundedRect(self.rect(), 12, 12)
        d = 18
        x = self.width() - d - 3 if self.isChecked() else 3
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(x, 3, d, d)


class DurationPicker(QWidget):
    """Preset chips (30 s ... 10 min) plus a custom minutes/seconds entry."""

    changed = Signal()

    def __init__(self, t, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._buttons = {}
        for i, key in enumerate(PRESET_ORDER):
            btn = QPushButton(t("dur_" + key))
            btn.setCheckable(True)
            btn.setProperty("chip", "true")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(36)
            self.group.addButton(btn, i)
            self._buttons[key] = btn
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)
        self.group.idClicked.connect(self._on_clicked)

        self.custom_row = QWidget()
        row = QHBoxLayout(self.custom_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 600)
        self.min_spin.setValue(3)
        self.sec_spin = QSpinBox()
        self.sec_spin.setRange(0, 59)
        row.addWidget(self.min_spin)
        row.addWidget(make_label(t("unit_min"), muted=True))
        row.addSpacing(6)
        row.addWidget(self.sec_spin)
        row.addWidget(make_label(t("unit_sec"), muted=True))
        row.addStretch(1)
        layout.addWidget(self.custom_row)
        self.min_spin.valueChanged.connect(lambda _v: self.changed.emit())
        self.sec_spin.valueChanged.connect(lambda _v: self.changed.emit())

        self._buttons["1m"].setChecked(True)
        self.custom_row.setVisible(False)

    # ---- state ---------------------------------------------------------
    def preset(self):
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return "1m"

    def custom_seconds(self):
        return self.min_spin.value() * 60 + self.sec_spin.value()

    def seconds(self):
        preset = self.preset()
        return PRESETS[preset] if preset in PRESETS else self.custom_seconds()

    def set_value(self, preset, custom_seconds):
        """Set the state without emitting `changed`."""
        self.blockSignals(True)
        self.min_spin.blockSignals(True)
        self.sec_spin.blockSignals(True)
        preset = preset if preset in self._buttons else "1m"
        self._buttons[preset].setChecked(True)
        self.min_spin.setValue(int(custom_seconds) // 60)
        self.sec_spin.setValue(int(custom_seconds) % 60)
        self.custom_row.setVisible(preset == "custom")
        self.min_spin.blockSignals(False)
        self.sec_spin.blockSignals(False)
        self.blockSignals(False)

    def _on_clicked(self, _id):
        self.custom_row.setVisible(self.preset() == "custom")
        self.changed.emit()


class ChipGroup(QWidget):
    """Exclusive row of chips (segmented choice). items = [(key, label), ...]."""

    changed = Signal()

    def __init__(self, items, columns=None, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        columns = columns or len(items)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._buttons = {}
        for i, (key, label) in enumerate(items):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("chip", "true")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(36)
            self.group.addButton(btn, i)
            self._buttons[key] = btn
            grid.addWidget(btn, i // columns, i % columns)
        self._keys = [key for key, _label in items]
        self._buttons[self._keys[0]].setChecked(True)
        self.group.idClicked.connect(lambda _id: self.changed.emit())

    def value(self):
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return self._keys[0]

    def set_value(self, key):
        """Select a chip without emitting `changed`."""
        key = key if key in self._buttons else self._keys[0]
        self.blockSignals(True)
        self._buttons[key].setChecked(True)
        self.blockSignals(False)


class SliderRow(QWidget):
    """Title + current value on one line, the slider below and an optional help text."""

    changed = Signal(int)

    def __init__(self, title, minimum, maximum, formatter=None, help_text="", parent=None):
        super().__init__(parent)
        self._format = formatter or (lambda v: f"{v}")
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        head = QHBoxLayout()
        head.addWidget(make_label(title, "rowTitle"), 1)
        self.value_label = make_label("", "statValue")
        head.addWidget(self.value_label)
        col.addLayout(head)
        if help_text:
            col.addWidget(make_label(help_text, muted=True, wrap=True))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        col.addWidget(self.slider)
        self.slider.valueChanged.connect(self._on_changed)
        self._on_changed(self.slider.value())

    def _on_changed(self, value):
        self.value_label.setText(self._format(value))
        self.changed.emit(value)

    def value(self):
        return self.slider.value()

    def set_value(self, value):
        """Set the slider without emitting `changed`."""
        self.slider.blockSignals(True)
        self.slider.setValue(int(value))
        self.slider.blockSignals(False)
        self.value_label.setText(self._format(self.slider.value()))
