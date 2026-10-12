"""Interface texts in English and Spanish (chosen from the system language)."""

EN = {
    "app_tagline": "Type any text into any app — naturally.",
    "text_label": "Text to type",
    "text_placeholder": "Paste or type the text you want AutoTyper to write…",
    "paste": "Paste",
    "clear": "Clear",
    "count": "{n} characters · {w} words",
    "duration_label": "Duration",
    "dur_30s": "30 sec", "dur_1m": "1 min", "dur_2m": "2 min",
    "dur_5m": "5 min", "dur_10m": "10 min", "dur_custom": "Custom",
    "unit_min": "min", "unit_sec": "sec",
    "speed": "≈ {cps} chars/sec · ≈ {wpm} words/min",
    "speed_none": "Add some text to see the typing speed",
    "speed_fast": "Very fast — some apps may drop characters. Try a longer duration.",
    "start": "Start",
    "stop": "Stop",
    "stop_hint": "Press {key} to stop instantly",
    "status_label": "Status",
    "state_ready": "Ready",
    "state_countdown": "Starting in {n}…",
    "state_typing": "Typing…",
    "state_done": "Done",
    "state_stopped": "Stopped",
    "state_error": "Error",
    "hint_ready": "Paste your text, choose a duration and press Start.",
    "hint_countdown": "Now click into the app and text field where the text should appear.",
    "hint_typing": "Press {key} or Stop to stop immediately.",
    "chars_typed": "Characters typed",
    "progress": "Progress",
    "time_remaining": "Time remaining",
    "msg_done": "Finished typing {n} characters.",
    "msg_stopped": "Typing stopped. {n} of {total} characters were typed.",
    "abort_own_window": ("Nothing more was typed because AutoTyper was the active window. "
                         "After pressing Start, click into your target app."),
    "err_empty": "Paste some text first.",
    "err_duration": "Choose a duration greater than zero.",
    "settings_title": "Settings",
    "back": "Back",
    "set_duration": "Default duration",
    "set_duration_help": "How long the whole text takes to type",
    "set_variation": "Natural speed variation",
    "set_variation_help": "0% = perfectly even rhythm · 100% = most human",
    "set_stop_key": "Stop shortcut",
    "set_stop_help": "Works even while another app is active",
    "set_stop_key_mac": ("On many Macs you need to hold Fn (Fn+F8), or turn on “Use F1, F2, etc. "
                         "keys as standard function keys” in System Settings → Keyboard."),
    "set_theme": "Theme",
    "theme_system": "System", "theme_light": "Light", "theme_dark": "Dark",
    "set_on_top": "Keep window on top",
    "set_language": "Language",
    "lang_auto": "Automatic", "lang_es": "Español", "lang_en": "English",
    "lang_restart": "Restart AutoTyper to apply the language.",
    "tip_theme": "Switch light / dark theme",
    "tip_settings": "Settings",
    "perm_title": "Allow AutoTyper to type",
    "perm_intro": "macOS blocks apps from typing into other apps until you allow it. It takes about 30 seconds:",
    "perm_step1": "1.  Click “Open System Settings” below.",
    "perm_step2": "2.  Go to Privacy & Security → Accessibility.",
    "perm_step3": "3.  Turn on the switch next to AutoTyper (use + to add it from Applications if it is not listed).",
    "perm_step4": "4.  Come back here and click “Check again”.",
    "perm_tip": ("Already on but still not working? Select AutoTyper in the list, remove it with −, "
                 "add it again and restart AutoTyper."),
    "perm_open": "Open System Settings",
    "perm_check": "Check again",
    "perm_input": ("Recommended: so the stop shortcut also works while another app is active, allow "
                   "AutoTyper under Privacy & Security → Input Monitoring."),
    "perm_open_input": "Open Input Monitoring",
    "set_perm_section": "macOS permissions",
    "perm_accessibility": "Accessibility (needed to type)",
    "perm_input_monitoring": "Input Monitoring (for the stop shortcut)",
    "perm_granted": "Allowed",
    "perm_not_granted": "Not allowed",
    "unsupported_os": "AutoTyper can type on Windows and macOS only.",
}

ES = {
    "app_tagline": "Escribe cualquier texto en cualquier app, de forma natural.",
    "text_label": "Texto a escribir",
    "text_placeholder": "Pega o escribe aquí el texto que quieres que AutoTyper escriba…",
    "paste": "Pegar",
    "clear": "Borrar",
    "count": "{n} caracteres · {w} palabras",
    "duration_label": "Duración",
    "dur_30s": "30 s", "dur_1m": "1 min", "dur_2m": "2 min",
    "dur_5m": "5 min", "dur_10m": "10 min", "dur_custom": "Personalizada",
    "unit_min": "min", "unit_sec": "seg",
    "speed": "≈ {cps} caracteres/s · ≈ {wpm} palabras/min",
    "speed_none": "Añade texto para ver la velocidad de escritura",
    "speed_fast": "Muy rápido: algunas apps pueden perder caracteres. Prueba con más tiempo.",
    "start": "Start",
    "stop": "Stop",
    "stop_hint": "Pulsa {key} para detener al instante",
    "status_label": "Estado",
    "state_ready": "Listo",
    "state_countdown": "Empezando en {n}…",
    "state_typing": "Escribiendo…",
    "state_done": "Terminado",
    "state_stopped": "Detenido",
    "state_error": "Error",
    "hint_ready": "Pega tu texto, elige una duración y pulsa Start.",
    "hint_countdown": "Haz clic ahora en la app y el campo donde debe aparecer el texto.",
    "hint_typing": "Pulsa {key} o Stop para detener al instante.",
    "chars_typed": "Caracteres escritos",
    "progress": "Progreso",
    "time_remaining": "Tiempo restante",
    "msg_done": "Terminado: se escribieron {n} caracteres.",
    "msg_stopped": "Escritura detenida. Se escribieron {n} de {total} caracteres.",
    "abort_own_window": ("No se escribió nada más porque AutoTyper era la ventana activa. "
                         "Después de pulsar Start, haz clic en la app de destino."),
    "err_empty": "Pega primero algo de texto.",
    "err_duration": "Elige una duración mayor que cero.",
    "settings_title": "Ajustes",
    "back": "Volver",
    "set_duration": "Duración predeterminada",
    "set_duration_help": "Cuánto tarda en escribirse todo el texto",
    "set_variation": "Variación natural de velocidad",
    "set_variation_help": "0 % = ritmo totalmente uniforme · 100 % = lo más humano",
    "set_stop_key": "Atajo para detener",
    "set_stop_help": "Funciona aunque otra app esté activa",
    "set_stop_key_mac": ("En muchos Mac hay que mantener Fn (Fn+F8), o activar «Usar las teclas F1, F2, etc. "
                         "como teclas de función estándar» en Ajustes del Sistema → Teclado."),
    "set_theme": "Tema",
    "theme_system": "Sistema", "theme_light": "Claro", "theme_dark": "Oscuro",
    "set_on_top": "Mantener ventana encima",
    "set_language": "Idioma",
    "lang_auto": "Automático", "lang_es": "Español", "lang_en": "English",
    "lang_restart": "Reinicia AutoTyper para aplicar el idioma.",
    "tip_theme": "Cambiar entre tema claro y oscuro",
    "tip_settings": "Ajustes",
    "perm_title": "Permite que AutoTyper escriba",
    "perm_intro": "macOS impide que una app escriba en otras apps hasta que lo permitas. Tarda unos 30 segundos:",
    "perm_step1": "1.  Pulsa «Abrir Ajustes del Sistema» aquí abajo.",
    "perm_step2": "2.  Ve a Privacidad y seguridad → Accesibilidad.",
    "perm_step3": "3.  Activa el interruptor junto a AutoTyper (si no aparece, pulsa + y añádelo desde Aplicaciones).",
    "perm_step4": "4.  Vuelve aquí y pulsa «Comprobar de nuevo».",
    "perm_tip": ("¿Ya está activado pero no funciona? Selecciona AutoTyper en la lista, quítalo con −, "
                 "vuelve a añadirlo y reinicia AutoTyper."),
    "perm_open": "Abrir Ajustes del Sistema",
    "perm_check": "Comprobar de nuevo",
    "perm_input": ("Recomendado: para que el atajo de parada también funcione con otra app activa, permite "
                   "AutoTyper en Privacidad y seguridad → Monitorización de entrada."),
    "perm_open_input": "Abrir Monitorización de entrada",
    "set_perm_section": "Permisos de macOS",
    "perm_accessibility": "Accesibilidad (necesario para escribir)",
    "perm_input_monitoring": "Monitorización de entrada (para el atajo de parada)",
    "perm_granted": "Permitido",
    "perm_not_granted": "No permitido",
    "unsupported_os": "AutoTyper solo puede escribir en Windows y macOS.",
}

EN.update({
    "tab_typing": "Typing", "tab_humanize": "Humanization",
    "tab_corrections": "Corrections", "tab_settings": "Settings",
    "pause": "Pause", "resume": "Resume",
    "elapsed": "Elapsed",
    "state_paused": "Paused",
    "state_resuming": "Resuming in {n}…",
    "hint_paused": "Press Resume or {key} to continue. A short countdown lets you click back into your app.",
    "hint_paused_own": ("AutoTyper became the active window, so typing paused. "
                        "Click Resume, then click back into your app."),
    "hint_resuming": "Click into the app where the text should continue.",
    "msg_focus": "Stopped because the active window changed.",
    "msg_stray": "{n} character(s) of a simulated typo may remain where you were typing; delete them manually.",
    "msg_done_typos": "Finished typing {n} characters, including {m} simulated typo(s) that were corrected.",
    "human_title": "Humanize typing",
    "human_help": ("Adds a natural rhythm: uneven keystrokes, pauses at words, punctuation and paragraphs, "
                   "and the occasional thinking pause. Off = perfectly steady speed."),
    "human_style": "Style",
    "style_steady": "Steady", "style_natural": "Natural", "style_thoughtful": "Slow & Thoughtful",
    "style_steady_help": "Even, calm rhythm with very little variation.",
    "style_natural_help": "Like a typical person: small variations and pauses at the end of words and sentences.",
    "style_thoughtful_help": "Slower pace with longer pauses and more frequent moments of thinking.",
    "human_level": "Intensity",
    "level_low": "Low", "level_medium": "Medium", "level_high": "High", "level_custom": "Custom",
    "cust_variation": "Speed variation",
    "cust_pauses": "Word & sentence pauses",
    "cust_thinking": "Thinking pauses",
    "human_note": "The total time you choose is always respected; humanization only changes how it is distributed.",
    "typo_title": "Simulate typos & corrections",
    "typo_help": ("Occasionally types a wrong letter, pauses, deletes only what it just typed and types the "
                  "right one. The text in the editor is never changed."),
    "typo_rate": "Frequency",
    "typo_rate_help": "Share of words that get a mistake",
    "typo_delay": "Correction delay",
    "typo_delay_help": "How long it “notices” the mistake before fixing it",
    "typo_safety_title": "Safety",
    "typo_safety": ("Corrections only delete characters AutoTyper itself just typed, never anything that was "
                    "already in your document. Typing stops at once if the active window changes or a key "
                    "press fails."),
    "typo_stop_note": ("If you stop with the Stop button while a typo is on screen, up to a few extra letters "
                       "can stay behind; stopping with the keyboard shortcut cleans them up."),
    "set_pause_key": "Pause shortcut",
    "set_pause_help": "Press once to pause, again to resume",
    "set_focus": "Stop if the active window changes",
    "set_focus_help": "Protects against typing into the wrong app. Always on when corrections are enabled.",
})

ES.update({
    "tab_typing": "Escritura", "tab_humanize": "Humanización",
    "tab_corrections": "Correcciones", "tab_settings": "Ajustes",
    "pause": "Pausa", "resume": "Continuar",
    "elapsed": "Transcurrido",
    "state_paused": "En pausa",
    "state_resuming": "Reanudando en {n}…",
    "hint_paused": ("Pulsa Continuar o {key} para seguir. Una cuenta atrás corta te deja volver a hacer "
                    "clic en tu app."),
    "hint_paused_own": ("AutoTyper pasó a ser la ventana activa, así que la escritura se pausó. "
                        "Pulsa Continuar y vuelve a hacer clic en tu app."),
    "hint_resuming": "Haz clic en la app donde debe continuar el texto.",
    "msg_focus": "Detenido porque cambió la ventana activa.",
    "msg_stray": "Pueden quedar {n} carácter(es) de una errata simulada donde estabas escribiendo; bórralos a mano.",
    "msg_done_typos": "Terminado: se escribieron {n} caracteres, con {m} errata(s) simulada(s) ya corregida(s).",
    "human_title": "Humanizar la escritura",
    "human_help": ("Añade un ritmo natural: pulsaciones irregulares, pausas en palabras, puntuación y párrafos, "
                   "y alguna pausa para pensar. Desactivado = velocidad perfectamente constante."),
    "human_style": "Estilo",
    "style_steady": "Constante", "style_natural": "Natural", "style_thoughtful": "Lento y reflexivo",
    "style_steady_help": "Ritmo tranquilo y uniforme, con muy poca variación.",
    "style_natural_help": "Como una persona normal: pequeñas variaciones y pausas al final de palabras y frases.",
    "style_thoughtful_help": "Ritmo más lento, con pausas más largas y momentos de reflexión más frecuentes.",
    "human_level": "Intensidad",
    "level_low": "Baja", "level_medium": "Media", "level_high": "Alta", "level_custom": "Personalizada",
    "cust_variation": "Variación de velocidad",
    "cust_pauses": "Pausas de palabras y frases",
    "cust_thinking": "Pausas para pensar",
    "human_note": "El tiempo total que elijas siempre se respeta; la humanización solo cambia cómo se reparte.",
    "typo_title": "Simular erratas y correcciones",
    "typo_help": ("De vez en cuando escribe una letra equivocada, hace una pausa, borra solo lo que acaba de "
                  "escribir y pone la correcta. El texto del editor nunca se modifica."),
    "typo_rate": "Frecuencia",
    "typo_rate_help": "Porcentaje de palabras que llevan una errata",
    "typo_delay": "Retraso de corrección",
    "typo_delay_help": "Cuánto tarda en «darse cuenta» del error antes de corregirlo",
    "typo_safety_title": "Seguridad",
    "typo_safety": ("Las correcciones solo borran caracteres que AutoTyper acaba de escribir, nunca nada que ya "
                    "estuviera en tu documento. La escritura se detiene al instante si cambia la ventana activa "
                    "o falla una pulsación."),
    "typo_stop_note": ("Si detienes con el botón Stop mientras hay una errata en pantalla, pueden quedar unas "
                       "pocas letras de más; si detienes con el atajo de teclado, se limpian solas."),
    "set_pause_key": "Atajo de pausa",
    "set_pause_help": "Pulsa una vez para pausar y otra para continuar",
    "set_focus": "Detener si cambia la ventana activa",
    "set_focus_help": ("Evita escribir en la app equivocada. Siempre activo cuando las correcciones están "
                       "activadas."),
})

STRINGS = {"en": EN, "es": ES}


def detect_language(locale_name):
    """'es_CO' -> 'es'; anything that is not Spanish -> 'en'."""
    return "es" if str(locale_name or "").lower().startswith("es") else "en"


def fmt_int(n, lang="en"):
    s = f"{int(n):,}"
    return s.replace(",", ".") if lang == "es" else s


class Translator:
    def __init__(self, lang="en"):
        self.lang = lang if lang in STRINGS else "en"

    def __call__(self, key, /, **kwargs):  # positional-only: `key` is also a valid placeholder name
        text = STRINGS[self.lang].get(key) or EN.get(key) or key
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError, ValueError):
            return text
