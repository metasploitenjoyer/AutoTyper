"""Humanization tab: natural typing rhythm (style, intensity and custom sliders)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from .widgets import Card, ChipGroup, SliderRow, Switch, make_label


def scroll_page(widget_builder):
    """Wrap page content in a transparent scroll area; returns (scroll area, column layout)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = QWidget()
    content.setObjectName("scrollContent")
    col = QVBoxLayout(content)
    col.setContentsMargins(0, 0, 6, 0)
    col.setSpacing(14)
    widget_builder(col)
    col.addStretch(1)
    scroll.setWidget(content)
    return scroll


class HumanizePage(QWidget):
    changed = Signal()

    def __init__(self, t, parent=None):
        super().__init__(parent)
        self.t = t
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(self._build))

    def _build(self, col):
        t = self.t
        # on / off
        top = Card()
        row = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(make_label(t("human_title"), "h2"))
        left.addWidget(make_label(t("human_help"), muted=True, wrap=True))
        row.addLayout(left, 1)
        self.enable_switch = Switch()
        row.addWidget(self.enable_switch, 0, Qt.AlignmentFlag.AlignTop)
        top.body.addLayout(row)
        col.addWidget(top)

        # style + intensity
        self.options = Card()
        self.options.body.addWidget(make_label(t("human_style"), "rowTitle"))
        self.style_chips = ChipGroup([("steady", t("style_steady")), ("natural", t("style_natural")),
                                      ("thoughtful", t("style_thoughtful"))])
        self.options.body.addWidget(self.style_chips)
        self.style_help = make_label("", muted=True, wrap=True)
        self.options.body.addWidget(self.style_help)

        self.options.body.addWidget(make_label(t("human_level"), "rowTitle"))
        self.level_chips = ChipGroup([("low", t("level_low")), ("medium", t("level_medium")),
                                      ("high", t("level_high")), ("custom", t("level_custom"))])
        self.options.body.addWidget(self.level_chips)

        self.custom_box = QWidget()
        cb = QVBoxLayout(self.custom_box)
        cb.setContentsMargins(0, 4, 0, 0)
        cb.setSpacing(12)
        pct = lambda v: f"{v}%"  # noqa: E731
        self.var_slider = SliderRow(t("cust_variation"), 0, 100, pct)
        self.pause_slider = SliderRow(t("cust_pauses"), 0, 100, pct)
        self.think_slider = SliderRow(t("cust_thinking"), 0, 100, pct)
        for w in (self.var_slider, self.pause_slider, self.think_slider):
            cb.addWidget(w)
        self.options.body.addWidget(self.custom_box)
        self.options.body.addWidget(make_label(t("human_note"), muted=True, wrap=True))
        col.addWidget(self.options)

        self.enable_switch.toggled.connect(self._on_edit)
        self.style_chips.changed.connect(self._on_edit)
        self.level_chips.changed.connect(self._on_edit)
        for slider in (self.var_slider, self.pause_slider, self.think_slider):
            slider.changed.connect(lambda _v: self._on_edit())

    def _on_edit(self, *_args):
        self._sync_visibility()
        self.changed.emit()

    def _sync_visibility(self):
        self.options.setEnabled(self.enable_switch.isChecked())
        self.custom_box.setVisible(self.level_chips.value() == "custom")
        self.style_help.setText(self.t("style_" + self.style_chips.value() + "_help"))

    def load(self, s):
        """Show the settings without emitting `changed`."""
        self.enable_switch.blockSignals(True)
        self.enable_switch.setChecked(s.humanize)
        self.enable_switch.blockSignals(False)
        self.style_chips.set_value(s.human_style)
        self.level_chips.set_value(s.human_level)
        self.var_slider.set_value(s.variation)
        self.pause_slider.set_value(s.custom_pauses)
        self.think_slider.set_value(s.custom_thinking)
        self._sync_visibility()

    def apply_to(self, s):
        s.humanize = self.enable_switch.isChecked()
        s.human_style = self.style_chips.value()
        s.human_level = self.level_chips.value()
        s.variation = self.var_slider.value()
        s.custom_pauses = self.pause_slider.value()
        s.custom_thinking = self.think_slider.value()
