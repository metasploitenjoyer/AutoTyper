"""The main AutoTyper window."""

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (QApplication, QBoxLayout, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                               QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QStackedWidget,
                               QVBoxLayout, QWidget)

from ..engine import TypingSession, fmt_time, typing_speed
from ..humanize import build_profile
from ..i18n import fmt_int
from ..plan import TypoConfig
from ..resources import resource_path
from ..settings import distinct_keys
from .corrections_page import CorrectionsPage
from .humanize_page import HumanizePage
from .icons import make_icon, render_image
from .permission_panel import PermissionPanel
from .settings_page import SettingsPage
from .theme import PALETTES, apply_theme, resolve_theme, system_is_dark
from .widgets import Card, DurationPicker, make_label

FAST_CPS = 20.0               # above this speed some apps start dropping characters
WIDE_LAYOUT_MIN_WIDTH = 880   # side-by-side layout from this width, stacked below it


class MainWindow(QWidget):
    def __init__(self, settings, backend, t, lang="en", settings_path=None, countdown=5, resume_countdown=3):
        super().__init__()
        self.settings = settings
        self.backend = backend
        self.t = t
        self.lang = lang
        self._settings_path = settings_path
        self._countdown = countdown
        self._resume_countdown = resume_countdown
        self.session = None
        self._notice = ""
        self._text_len = 0
        self._app_active = False
        self._resolved = "light"
        self._pal = PALETTES["light"]
        self._icon_targets = []
        self._horizontal = None
        self._dot_css = None

        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("AutoTyper")

        self._build()
        self._connect_settings_page()
        self.settings_page.load(settings)
        self.human_page.load(settings)
        self.typo_page.load(settings)
        self.picker.set_value(settings.duration_preset, settings.custom_seconds)
        self._apply_theme()
        self._apply_on_top(settings.always_on_top)
        self._update_stop_hint()
        self._update_text_stats()
        self._size_to_screen()
        self._connect_app_signals()
        self._update_permissions()

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start()
        if backend.needs_permissions:
            self._perm_timer = QTimer(self)
            self._perm_timer.setInterval(2000)
            self._perm_timer.timeout.connect(self._update_permissions)
            self._perm_timer.start()

    # ==================================================================
    # Layout
    # ==================================================================
    def _button(self, text, name=None, icon=None, color_key="text", ghost=False, iconbtn=False):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if name:
            btn.setObjectName(name)
        if ghost:
            btn.setProperty("ghost", "true")
        if iconbtn:
            btn.setProperty("iconbtn", "true")
        if icon:
            btn.setIconSize(QSize(18, 18))
            self._icon_targets.append((btn, icon, color_key))
        return btn

    def _build(self):
        t = self.t
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        outer.setSpacing(14)
        outer.addLayout(self._build_header())
        outer.addLayout(self._build_tabs())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_main_page())          # 0  Typing
        self.human_page = HumanizePage(t)                      # 1  Humanization
        self.stack.addWidget(self.human_page)
        self.typo_page = CorrectionsPage(t)                    # 2  Corrections
        self.stack.addWidget(self.typo_page)
        self.settings_page = SettingsPage(t, self.backend)     # 3  Settings
        self._icon_targets.extend(self.settings_page.icon_targets)
        self.stack.addWidget(self.settings_page)
        outer.addWidget(self.stack, 1)
        self.tab_group.idClicked.connect(self.stack.setCurrentIndex)   # the stack exists now

    def _build_tabs(self):
        row = QHBoxLayout()
        row.setSpacing(6)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_buttons = []
        for index, key in enumerate(("tab_typing", "tab_humanize", "tab_corrections", "tab_settings")):
            btn = QPushButton(self.t(key))
            btn.setCheckable(True)
            btn.setProperty("tab", "true")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.tab_group.addButton(btn, index)
            self.tab_buttons.append(btn)
            row.addWidget(btn)
        self.tab_buttons[0].setChecked(True)
        row.addStretch(1)
        return row

    def show_tab(self, index):
        self.tab_buttons[index].setChecked(True)
        self.stack.setCurrentIndex(index)

    def _build_header(self):
        t = self.t
        row = QHBoxLayout()
        row.setSpacing(12)

        logo = make_label("")
        pm = QPixmap(str(resource_path("assets", "icons", "icon.png")))
        if not pm.isNull():
            pm = pm.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(2)
            logo.setPixmap(pm)
        logo.setFixedSize(40, 40)
        row.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(make_label("AutoTyper", "title"))
        titles.addWidget(make_label(t("app_tagline"), muted=True))
        row.addLayout(titles, 1)

        self.theme_btn = self._button("", iconbtn=True)
        self.theme_btn.setIconSize(QSize(18, 18))
        self.theme_btn.setToolTip(t("tip_theme"))
        self.theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self.theme_btn)
        return row

    def _build_main_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("scrollContent")
        col = QVBoxLayout(content)
        col.setContentsMargins(0, 0, 6, 0)
        col.setSpacing(14)

        self.perm_panel = PermissionPanel(self.t)
        self.perm_panel.hide()
        col.addWidget(self.perm_panel)

        host = QWidget()
        self.body = QBoxLayout(QBoxLayout.Direction.LeftToRight, host)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(16)
        self.text_card = self._build_text_card()
        self.side = self._build_side()
        self.body.addWidget(self.text_card, 1)
        self.body.addWidget(self.side, 0)
        col.addWidget(host, 1)

        scroll.setWidget(content)
        return scroll

    def _build_text_card(self):
        t = self.t
        card = Card()
        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(make_label(t("text_label"), "h2"), 1)
        paste_btn = self._button(t("paste"), icon="paste", color_key="muted", ghost=True)
        clear_btn = self._button(t("clear"), icon="trash", color_key="muted", ghost=True)
        paste_btn.clicked.connect(self._paste)
        clear_btn.clicked.connect(self._clear)
        head.addWidget(paste_btn)
        head.addWidget(clear_btn)
        card.body.addLayout(head)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("editor")
        self.editor.setPlaceholderText(t("text_placeholder"))
        self.editor.setMinimumHeight(200)
        self.editor.textChanged.connect(self._on_text_changed)
        card.body.addWidget(self.editor, 1)

        self.count_label = make_label("", muted=True)
        card.body.addWidget(self.count_label)
        return card

    def _build_side(self):
        t = self.t
        side = QWidget()
        col = QVBoxLayout(side)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(14)

        # --- duration + speed
        dur = Card()
        dur.body.addWidget(make_label(t("duration_label"), "h2"))
        self.picker = DurationPicker(t)
        self.picker.changed.connect(self._on_main_duration)
        dur.body.addWidget(self.picker)
        speed_row = QHBoxLayout()
        speed_row.setSpacing(6)
        self.clock_label = make_label("")
        self.clock_label.setFixedSize(16, 16)
        self.speed_label = make_label("", muted=True, wrap=True)
        speed_row.addWidget(self.clock_label)
        speed_row.addWidget(self.speed_label, 1)
        dur.body.addLayout(speed_row)
        self.speed_warn = make_label(t("speed_fast"), muted=True, wrap=True)
        self.speed_warn.hide()
        dur.body.addWidget(self.speed_warn)
        col.addWidget(dur)

        # --- actions
        actions = Card()
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.start_btn = self._button(t("start"), "primary", icon="play", color_key="#FFFFFF")
        self.pause_btn = self._button(t("pause"), icon="pause", color_key="text")
        self.stop_btn = self._button(t("stop"), "danger", icon="stop", color_key="danger")
        self.start_btn.clicked.connect(self._on_start)
        self.pause_btn.clicked.connect(self._on_pause_toggle)
        self.stop_btn.clicked.connect(self._on_stop)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.start_btn, 3)
        buttons.addWidget(self.pause_btn, 2)
        buttons.addWidget(self.stop_btn, 2)
        actions.body.addLayout(buttons)
        self.stop_hint = make_label("", muted=True, wrap=True)
        actions.body.addWidget(self.stop_hint)
        col.addWidget(actions)

        # --- status + progress
        status = Card()
        status.body.addWidget(make_label(t("status_label"), "h2"))
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.status_dot = make_label("")
        self.status_dot.setFixedSize(12, 12)
        self.status_title = make_label("", "statusTitle")
        title_row.addWidget(self.status_dot)
        title_row.addWidget(self.status_title, 1)
        status.body.addLayout(title_row)
        self.status_hint = make_label("", muted=True, wrap=True)
        status.body.addWidget(self.status_hint)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        status.body.addWidget(self.bar)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        self.chars_value = self._stat_row(grid, 0, t("chars_typed"))
        self.pct_value = self._stat_row(grid, 1, t("progress"))
        self.elapsed_value = self._stat_row(grid, 2, t("elapsed"))
        self.time_value = self._stat_row(grid, 3, t("time_remaining"))
        status.body.addLayout(grid)
        col.addWidget(status)

        col.addStretch(1)
        return side

    def _stat_row(self, grid, row, text):
        grid.addWidget(make_label(text, muted=True), row, 0)
        value = make_label("", "statValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(value, row, 1)
        return value

    # ---- adapt to the screen -------------------------------------------
    def _size_to_screen(self):
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1280, 800)
        w = max(520, min(1040, int(avail.width() * 0.72)))
        h = max(560, min(760, int(avail.height() * 0.82)))
        self.setMinimumSize(480, 520)
        self.resize(w, h)
        self.move(avail.center() - self.rect().center())
        self._update_layout_mode()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_layout_mode()

    def _update_layout_mode(self):
        horizontal = self.width() >= WIDE_LAYOUT_MIN_WIDTH
        if horizontal == self._horizontal:
            return
        self._horizontal = horizontal
        self.body.setDirection(QBoxLayout.Direction.LeftToRight if horizontal
                               else QBoxLayout.Direction.TopToBottom)
        self.side.setMinimumWidth(340 if horizontal else 0)
        self.side.setMaximumWidth(400 if horizontal else 16777215)

    # ==================================================================
    # Theme / icons
    # ==================================================================
    def _apply_theme(self):
        app = QApplication.instance()
        self._resolved = resolve_theme(self.settings.theme, system_is_dark(app))
        self._pal = apply_theme(app, self._resolved)
        self._refresh_icons()
        self._refresh_ui()

    def _refresh_icons(self):
        pal = self._pal
        for widget, name, key in self._icon_targets:
            color = key if key.startswith("#") else pal[key]
            widget.setIcon(make_icon(name, color))
        self.theme_btn.setIcon(make_icon("sun" if self._resolved == "dark" else "moon", pal["text"]))
        self.clock_label.setPixmap(QPixmap.fromImage(render_image("clock", pal["muted"], 16)))
        self.perm_panel.icon_label.setPixmap(QPixmap.fromImage(render_image("alert", pal["warning"], 20)))

    def _toggle_theme(self):
        self.settings.theme = "light" if self._resolved == "dark" else "dark"
        self.settings_page.set_theme(self.settings.theme)
        self._apply_theme()
        self._save()

    def _on_system_scheme(self, *_args):
        if self.settings.theme == "system":
            self._apply_theme()

    # ==================================================================
    # Settings
    # ==================================================================
    def _connect_settings_page(self):
        sp = self.settings_page
        sp.duration_changed.connect(self._on_default_duration)
        sp.stop_key_changed.connect(self._on_stop_key)
        sp.pause_key_changed.connect(self._on_pause_key)
        sp.focus_guard_changed.connect(self._on_focus_guard)
        sp.theme_changed.connect(self._on_theme)
        sp.on_top_changed.connect(self._on_on_top)
        sp.language_changed.connect(self._on_language)
        self.human_page.changed.connect(self._on_human_changed)
        self.typo_page.changed.connect(self._on_typo_changed)
        self.perm_panel.open_requested.connect(lambda: self.backend.open_permission_settings("accessibility"))
        self.perm_panel.open_input_requested.connect(
            lambda: self.backend.open_permission_settings("input_monitoring"))
        self.perm_panel.check_requested.connect(self._update_permissions)
        sp.open_accessibility.connect(lambda: self.backend.open_permission_settings("accessibility"))
        sp.open_input_monitoring.connect(lambda: self.backend.open_permission_settings("input_monitoring"))
        sp.check_permissions.connect(self._update_permissions)

    def _on_human_changed(self):
        self.human_page.apply_to(self.settings)
        self._save()

    def _on_typo_changed(self):
        self.typo_page.apply_to(self.settings)
        self._save()

    def _save(self):
        if self._settings_path:
            try:
                self.settings.save(self._settings_path)
            except OSError:
                pass

    def _store_duration(self, picker):
        self.settings.duration_preset = picker.preset()
        self.settings.custom_seconds = max(1, picker.custom_seconds())

    def _on_main_duration(self):
        self._store_duration(self.picker)
        self.settings_page.duration_picker.set_value(self.settings.duration_preset,
                                                     self.settings.custom_seconds)
        self._update_speed()
        self._save()

    def _on_default_duration(self):
        self._store_duration(self.settings_page.duration_picker)
        self.picker.set_value(self.settings.duration_preset, self.settings.custom_seconds)
        self._update_speed()
        self._save()

    def _on_stop_key(self, key):
        self.settings.stop_key = key
        self._fix_shortcuts(changed="stop")

    def _on_pause_key(self, key):
        self.settings.pause_key = key
        self._fix_shortcuts(changed="pause")

    def _fix_shortcuts(self, changed):
        """Stop and pause must be different keys. The emergency-stop key is never changed behind
        your back: if both end up the same, the PAUSE key moves to a free key."""
        s = self.settings
        if s.stop_key == s.pause_key:
            s.pause_key = distinct_keys(s.stop_key, s.pause_key, self.backend.available_stop_keys())
        self.settings_page.set_stop_keys(s.stop_key, s.pause_key)
        self._update_stop_hint()
        self._save()

    def _on_focus_guard(self, on):
        self.settings.stop_on_focus_change = bool(on)
        self._save()

    def _on_theme(self, name):
        self.settings.theme = name
        self._apply_theme()
        self._save()

    def _on_on_top(self, on):
        self.settings.always_on_top = bool(on)
        self._apply_on_top(on)
        self._save()

    def _on_language(self, code):
        self.settings.language = code  # applied the next time AutoTyper starts
        self._save()

    def _apply_on_top(self, on):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        if self.isVisible():  # changing window flags hides the window
            self.show()

    def _update_stop_hint(self):
        self.stop_hint.setText(self.t("stop_hint", key=self.settings.stop_key))

    # ==================================================================
    # macOS permissions
    # ==================================================================
    def _update_permissions(self):
        """Refresh the permission UI; True when typing into other apps is allowed."""
        if not self.backend.needs_permissions:
            return True
        status = self.backend.permissions()
        self.perm_panel.set_status(status)
        self.settings_page.set_permission_status(status)
        return status.accessibility

    # ==================================================================
    # Text box
    # ==================================================================
    def _current_text(self):
        text = self.editor.toPlainText()
        for old in ("\r\n", "\r", "\u2028", "\u2029"):
            text = text.replace(old, "\n")
        return text

    def _paste(self):
        self.editor.paste()

    def _clear(self):
        if not (self.session and self.session.is_running):
            self.editor.clear()

    def _on_text_changed(self):
        self._notice = ""
        self._update_text_stats()

    def _update_text_stats(self):
        text = self._current_text()
        self._text_len = len(text)
        words = len(text.split())
        self.count_label.setText(self.t("count", n=fmt_int(self._text_len, self.lang),
                                        w=fmt_int(words, self.lang)))
        self._update_speed()

    def _update_speed(self):
        secs = self.picker.seconds()
        if self._text_len <= 0 or secs <= 0:
            self.speed_label.setText(self.t("speed_none"))
            self.speed_warn.setVisible(False)
            return
        cps, wpm = typing_speed(self._text_len, secs)
        cps_text = f"{cps:.1f}"
        if self.lang == "es":
            cps_text = cps_text.replace(".", ",")
        self.speed_label.setText(self.t("speed", cps=cps_text, wpm=f"{wpm:.0f}"))
        self.speed_warn.setVisible(cps > FAST_CPS)

    # ==================================================================
    # Start / stop
    # ==================================================================
    def _is_qt_active(self):
        """True while AutoTyper is the frontmost app (updated by Qt, read from the worker thread)."""
        return self._app_active

    def _connect_app_signals(self):
        app = QGuiApplication.instance()
        self._app_active = app.applicationState() == Qt.ApplicationState.ApplicationActive
        app.applicationStateChanged.connect(self._on_app_state)
        signal = getattr(app.styleHints(), "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(self._on_system_scheme)

    def _on_app_state(self, state):
        self._app_active = state == Qt.ApplicationState.ApplicationActive

    def _on_start(self):
        if self.session and self.session.is_running:
            return
        text = self._current_text()
        if not text.strip():
            self._notice = self.t("err_empty")
            self._refresh_ui()
            return
        seconds = self.picker.seconds()
        if seconds <= 0:
            self._notice = self.t("err_duration")
            self._refresh_ui()
            return
        if not self._update_permissions():  # macOS: Accessibility missing
            self.backend.request_permissions()
            self.stack.setCurrentIndex(0)
            return

        self._notice = ""
        backend = self.backend
        cfg = self.settings
        stop_key, pause_key = cfg.stop_key, cfg.pause_key
        window_id = int(self.winId())  # read on the GUI thread; the worker only compares numbers
        profile = build_profile(cfg.humanize, cfg.human_style, cfg.human_level,
                                cfg.variation, cfg.custom_pauses, cfg.custom_thinking)
        typos = TypoConfig(enabled=cfg.typos, rate=cfg.typo_rate / 100.0,
                           correction_delay=cfg.typo_delay / 10.0)
        self.session = TypingSession(
            text, seconds, backend.send_char,
            countdown=self._countdown,
            stop_check=lambda: backend.is_stop_key_down(stop_key),
            pause_check=lambda: backend.is_stop_key_down(pause_key),
            own_window_check=lambda: self._is_qt_active() or backend.is_own_window_foreground(window_id) is True,
            own_window_message=self.t("abort_own_window"),
            focus_token=backend.foreground_token,
            stop_on_focus_change=cfg.stop_on_focus_change,
            profile=profile,
            typos=typos,
            send_backspace=backend.send_backspace,
            resume_countdown=self._resume_countdown,
        )
        self.session.start()
        self._refresh_ui()

    def _on_pause_toggle(self):
        s = self.session
        if s is None:
            return
        if s.state == TypingSession.PAUSED:
            s.resume()
        elif s.state == TypingSession.TYPING:
            s.pause()

    def _on_stop(self):
        if self.session is not None:
            self.session.stop()

    def closeEvent(self, event):
        if self.session is not None:
            self.session.stop()
        self._save()
        super().closeEvent(event)

    # ==================================================================
    # Live status
    # ==================================================================
    def _refresh_ui(self):
        t, s = self.t, self.session
        running = bool(s and s.is_running)
        key = self.settings.stop_key
        elapsed = 0.0

        if s is None:
            title, color = t("state_ready"), "muted"
            hint = self._notice or t("hint_ready")
            if self._notice:
                color = "warning"
            typed, total, remaining = 0, self._text_len, float(self.picker.seconds())
        else:
            typed, total, remaining, elapsed = s.typed, s.total, s.remaining(), s.elapsed()
            if s.state == TypingSession.COUNTDOWN:
                n = s.countdown_left or self._countdown
                title, color, hint = t("state_countdown", n=n), "warning", t("hint_countdown")
            elif s.state == TypingSession.TYPING:
                title, color, hint = t("state_typing"), "accent", t("hint_typing", key=key)
            elif s.state == TypingSession.PAUSED:
                title, color = t("state_paused"), "warning"
                hint = (t("hint_paused_own") if s.pause_reason == "own_window"
                        else t("hint_paused", key=self.settings.pause_key))
            elif s.state == TypingSession.RESUMING:
                title, color = t("state_resuming", n=s.countdown_left or self._resume_countdown), "warning"
                hint = t("hint_resuming")
            elif s.state == TypingSession.DONE:
                title, color = t("state_done"), "success"
                if s.typos_made:
                    hint = t("msg_done_typos", n=fmt_int(s.typed, self.lang), m=s.typos_made)
                else:
                    hint = t("msg_done", n=fmt_int(s.typed, self.lang))
            elif s.state == TypingSession.STOPPED:
                title, color = t("state_stopped"), "warning"
                if s.cause == "user":
                    hint = t("msg_stopped", n=fmt_int(s.typed, self.lang), total=fmt_int(s.total, self.lang))
                elif s.cause == "focus":
                    hint = t("msg_focus")
                else:
                    hint = s.message
                if s.stray:
                    hint += " " + t("msg_stray", n=s.stray)
            else:
                title, color, hint = t("state_error"), "danger", s.message
                if s.stray:
                    hint += " " + t("msg_stray", n=s.stray)

        self.status_title.setText(title)
        self.status_hint.setText(hint)
        dot_css = f"background: {self._pal[color]}; border-radius: 6px;"
        if dot_css != self._dot_css:  # re-styling every tick would be wasteful
            self._dot_css = dot_css
            self.status_dot.setStyleSheet(dot_css)

        pct = int(typed * 100 / total) if total else 0
        self.bar.setValue(pct)
        self.chars_value.setText(f"{fmt_int(typed, self.lang)} / {fmt_int(total, self.lang)}")
        self.pct_value.setText(f"{pct}%")
        self.elapsed_value.setText(fmt_time(elapsed))
        self.time_value.setText(fmt_time(remaining))

        paused = bool(s and s.state == TypingSession.PAUSED)
        self.start_btn.setEnabled(not running)
        self.pause_btn.setEnabled(bool(s and s.state in (TypingSession.TYPING, TypingSession.PAUSED)))
        self.pause_btn.setText(t("resume") if paused else t("pause"))
        self.stop_btn.setEnabled(running)
        self.editor.setReadOnly(running)
