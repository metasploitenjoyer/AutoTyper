"""Corrections tab: simulated typos that are typed, noticed and corrected."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from .humanize_page import scroll_page
from .widgets import Card, SliderRow, Switch, make_label


class CorrectionsPage(QWidget):
    changed = Signal()

    def __init__(self, t, parent=None):
        super().__init__(parent)
        self.t = t
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(self._build))

    def _build(self, col):
        t = self.t
        top = Card()
        row = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(make_label(t("typo_title"), "h2"))
        left.addWidget(make_label(t("typo_help"), muted=True, wrap=True))
        row.addLayout(left, 1)
        self.enable_switch = Switch()
        row.addWidget(self.enable_switch, 0, Qt.AlignmentFlag.AlignTop)
        top.body.addLayout(row)
        col.addWidget(top)

        self.options = Card()
        self.rate_slider = SliderRow(t("typo_rate"), 1, 30, lambda v: f"{v}%", t("typo_rate_help"))
        self.delay_slider = SliderRow(t("typo_delay"), 3, 50, lambda v: f"{v / 10:.1f} s", t("typo_delay_help"))
        self.options.body.addWidget(self.rate_slider)
        self.options.body.addWidget(self.delay_slider)
        col.addWidget(self.options)

        safety = Card()
        safety.body.addWidget(make_label(t("typo_safety_title"), "h2"))
        safety.body.addWidget(make_label(t("typo_safety"), wrap=True))
        safety.body.addWidget(make_label(t("typo_stop_note"), muted=True, wrap=True))
        col.addWidget(safety)

        self.enable_switch.toggled.connect(self._on_edit)
        self.rate_slider.changed.connect(lambda _v: self._on_edit())
        self.delay_slider.changed.connect(lambda _v: self._on_edit())

    def _on_edit(self, *_args):
        self.options.setEnabled(self.enable_switch.isChecked())
        self.changed.emit()

    def load(self, s):
        self.enable_switch.blockSignals(True)
        self.enable_switch.setChecked(s.typos)
        self.enable_switch.blockSignals(False)
        self.rate_slider.set_value(s.typo_rate)
        self.delay_slider.set_value(s.typo_delay)
        self.options.setEnabled(s.typos)

    def apply_to(self, s):
        s.typos = self.enable_switch.isChecked()
        s.typo_rate = self.rate_slider.value()
        s.typo_delay = self.delay_slider.value()
