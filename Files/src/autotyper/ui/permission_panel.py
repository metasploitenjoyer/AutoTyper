"""macOS banner that explains, step by step, how to allow AutoTyper to type."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton

from .widgets import Card, make_label


class PermissionPanel(Card):
    open_requested = Signal()
    check_requested = Signal()
    open_input_requested = Signal()

    def __init__(self, t, parent=None):
        super().__init__("warn", parent)
        self.icon_targets = []
        head = QHBoxLayout()
        head.setSpacing(8)
        self.icon_label = make_label("")
        self.icon_label.setFixedSize(22, 22)
        head.addWidget(self.icon_label)
        head.addWidget(make_label(t("perm_title"), "h2"), 1)
        self.body.addLayout(head)
        self.body.addWidget(make_label(t("perm_intro"), wrap=True))
        for key in ("perm_step1", "perm_step2", "perm_step3", "perm_step4"):
            self.body.addWidget(make_label(t(key), wrap=True))
        self.body.addWidget(make_label(t("perm_tip"), muted=True, wrap=True))

        self.input_label = make_label(t("perm_input"), wrap=True)
        self.body.addWidget(self.input_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.open_btn = QPushButton(t("perm_open"))
        self.open_btn.setObjectName("primary")
        self.check_btn = QPushButton(t("perm_check"))
        self.input_btn = QPushButton(t("perm_open_input"))
        for b in (self.open_btn, self.check_btn, self.input_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.check_btn)
        buttons.addWidget(self.input_btn)
        buttons.addStretch(1)
        self.body.addLayout(buttons)

        self.open_btn.clicked.connect(self.open_requested)
        self.check_btn.clicked.connect(self.check_requested)
        self.input_btn.clicked.connect(self.open_input_requested)
        self.icon_size = QSize(20, 20)

    def set_status(self, status):
        """Show only while Accessibility is missing; the Input Monitoring tip only if missing."""
        self.setVisible(not status.accessibility)
        self.input_label.setVisible(not status.input_monitoring)
        self.input_btn.setVisible(not status.input_monitoring)
