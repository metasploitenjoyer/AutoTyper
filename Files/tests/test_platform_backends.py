"""Windows vs macOS: backend selection, key events, stop-key tables and permissions."""

import ctypes
import unittest

import _path  # noqa: F401
from autotyper.i18n import EN, ES
from autotyper.system import backend_class, platform_key
from autotyper.system import macos, windows
from autotyper.system.base import DEFAULT_STOP_KEY, PermissionStatus, UnsupportedBackend

SAMPLE = "Hello, World!  Two  spaces.\nSecond line.\n\n\tTabbed — ñ é ü € “quotes” 😀 end."


class BackendSelectionTests(unittest.TestCase):
    def test_platform_detection(self):
        self.assertEqual(platform_key("win32"), "windows")
        self.assertEqual(platform_key("darwin"), "macos")
        self.assertEqual(platform_key("linux"), "unsupported")

    def test_each_os_gets_its_own_backend(self):
        self.assertIs(backend_class("win32"), windows.WindowsBackend)
        self.assertIs(backend_class("darwin"), macos.MacBackend)
        self.assertIs(backend_class("linux"), UnsupportedBackend)

    def test_backends_refuse_to_run_on_the_wrong_os(self):
        import sys
        if sys.platform != "win32":
            with self.assertRaises(RuntimeError):
                windows.WindowsBackend()
        if sys.platform != "darwin":
            with self.assertRaises(RuntimeError):
                macos.MacBackend()

    def test_unsupported_os_cannot_type_but_ui_still_works(self):
        be = UnsupportedBackend()
        with self.assertRaises(OSError):
            be.send_char("a")
        with self.assertRaises(OSError):
            be.send_backspace()
        self.assertIsNone(be.foreground_token())
        self.assertIn(DEFAULT_STOP_KEY, be.available_stop_keys())

    def test_capabilities_differ_as_expected(self):
        self.assertFalse(windows.WindowsBackend.needs_permissions)
        self.assertTrue(macos.MacBackend.needs_permissions)
        self.assertTrue(macos.MacBackend.fn_key_hint)
        self.assertFalse(windows.WindowsBackend.fn_key_hint)


class WindowsInputTests(unittest.TestCase):
    def test_enter_and_tab_are_real_keys(self):
        enter = windows.plan_char("\n")
        self.assertEqual([(e.vk, e.flags) for e in enter],
                         [(0x0D, 0), (0x0D, windows.KEYEVENTF_KEYUP)])
        tab = windows.plan_char("\t")
        self.assertEqual([e.vk for e in tab], [0x09, 0x09])

    def test_letters_use_unicode_events_so_case_and_punctuation_are_exact(self):
        for ch in "aA zZ.,;:!?¿¡'\"()-_ñÑéü€":
            ev = windows.plan_char(ch)
            self.assertEqual(len(ev), 2)
            self.assertEqual(ev[0].scan, ord(ch))
            self.assertEqual(ev[0].flags, windows.KEYEVENTF_UNICODE)
            self.assertEqual(ev[1].flags, windows.KEYEVENTF_UNICODE | windows.KEYEVENTF_KEYUP)
            self.assertEqual(ev[0].vk, 0)

    def test_characters_outside_the_bmp_use_surrogate_pairs(self):
        ev = windows.plan_char("😀")  # U+1F600 -> D83D DE00
        self.assertEqual([e.scan for e in ev], [0xD83D, 0xD83D, 0xDE00, 0xDE00])

    def test_plan_reproduces_the_text(self):
        typed, units = [], []
        for ch in SAMPLE:
            for e in windows.plan_char(ch):
                if e.flags & windows.KEYEVENTF_KEYUP:
                    continue
                if e.vk == windows.VK_RETURN:
                    typed.append("\n")
                elif e.vk == windows.VK_TAB:
                    typed.append("\t")
                else:
                    units.append(e.scan)
                    if not (0xD800 <= e.scan < 0xDC00):  # complete once the low surrogate arrives
                        typed.append(b"".join(u.to_bytes(2, "little") for u in units).decode("utf-16-le"))
                        units = []
        self.assertEqual("".join(typed), SAMPLE)

    def test_send_char_builds_correct_win32_structures(self):
        class FakeUser32:
            def __init__(self):
                self.batches = []

            def SendInput(self, n, arr, size):
                self.batches.append([(arr[i].type, arr[i].ki.wVk, arr[i].ki.wScan, arr[i].ki.dwFlags)
                                     for i in range(n)])
                return n

        fake = FakeUser32()
        be = windows.WindowsBackend(user32=fake)
        be.send_char("é")
        be.send_char("\n")
        self.assertEqual(fake.batches[0], [(1, 0, 0xE9, 4), (1, 0, 0xE9, 6)])
        self.assertEqual(fake.batches[1], [(1, 0x0D, 0, 0), (1, 0x0D, 0, 2)])

    def test_blocked_input_raises_a_helpful_error(self):
        class Blocked:
            def SendInput(self, n, arr, size):
                return 0

        with self.assertRaises(OSError) as ctx:
            windows.WindowsBackend(user32=Blocked()).send_char("a")
        self.assertIn("administrator", str(ctx.exception))

    def test_stop_keys(self):
        self.assertEqual(windows.VK_CODES["F8"], 0x77)
        self.assertEqual(windows.VK_CODES["F1"], 0x70)
        self.assertEqual(windows.VK_CODES["F12"], 0x7B)
        self.assertEqual(windows.VK_CODES["Esc"], 0x1B)
        self.assertIn("Pause", windows.WindowsBackend.stop_keys)

        class FakeUser32:
            down = set()

            def GetAsyncKeyState(self, vk):
                return -32768 if vk in self.down else 0  # high bit = key is down

        fake = FakeUser32()
        be = windows.WindowsBackend(user32=fake)
        self.assertFalse(be.is_stop_key_down("F8"))
        fake.down = {0x77}
        self.assertTrue(be.is_stop_key_down("F8"))
        self.assertFalse(be.is_stop_key_down("F9"))
        self.assertFalse(be.is_stop_key_down("nonsense"))

    def test_own_window_detection(self):
        class FakeUser32:
            fg = 100

            def GetForegroundWindow(self):
                return self.fg

            def GetAncestor(self, hwnd, flag):
                return hwnd

        fake = FakeUser32()
        be = windows.WindowsBackend(user32=fake)
        self.assertTrue(be.is_own_window_foreground(100))
        fake.fg = 200
        self.assertFalse(be.is_own_window_foreground(100))


    def test_backspace_is_a_real_key(self):
        self.assertEqual([(e.vk, e.flags) for e in windows.plan_backspace()],
                         [(0x08, 0), (0x08, windows.KEYEVENTF_KEYUP)])

    def test_send_backspace_and_foreground_token(self):
        class FakeUser32:
            def __init__(self):
                self.batches, self.fg = [], 300

            def SendInput(self, n, arr, size):
                self.batches.append([(arr[i].ki.wVk, arr[i].ki.wScan, arr[i].ki.dwFlags) for i in range(n)])
                return n

            def GetForegroundWindow(self):
                return self.fg

            def GetAncestor(self, hwnd, flag):
                return hwnd + 1          # the top-level (root) window of the focused control

        fake = FakeUser32()
        be = windows.WindowsBackend(user32=fake)
        be.send_backspace()
        self.assertEqual(fake.batches, [[(0x08, 0, 0), (0x08, 0, 2)]])
        self.assertEqual(be.foreground_token(), 301)
        fake.fg = 0
        self.assertIsNone(be.foreground_token())


class FakeCG:
    """Records the Quartz calls the macOS backend makes."""

    def __init__(self, trusted=True, listen=True, has_listen_api=True):
        self.calls, self._next, self.events = [], 1, {}
        self.keys_down = set()
        self._trusted, self._listen, self._has_listen_api = trusted, listen, has_listen_api

    def CGEventCreateKeyboardEvent(self, source, keycode, down):
        eid, self._next = self._next, self._next + 1
        self.events[eid] = {"keycode": keycode, "down": down, "text": None, "flags": None}
        return eid

    def CGEventKeyboardSetUnicodeString(self, event, length, units):
        self.events[event]["text"] = (length, list(units))

    def CGEventSetFlags(self, event, flags):
        self.events[event]["flags"] = flags

    def CGEventPost(self, tap, event):
        self.calls.append((tap, dict(self.events[event])))

    def CGEventSourceKeyState(self, state, keycode):
        return keycode in self.keys_down

    def AXIsProcessTrusted(self):
        return self._trusted

    def __getattr__(self, name):
        if name == "CGPreflightListenEventAccess" and self._has_listen_api:
            return lambda: self._listen
        raise AttributeError(name)


class FakeCF:
    def __init__(self):
        self.released = []

    def CFRelease(self, obj):
        self.released.append(obj)


class MacInputTests(unittest.TestCase):
    def test_enter_and_tab_are_real_keys(self):
        self.assertEqual(macos.plan_char("\n"), [macos.KeyPress(36)])
        self.assertEqual(macos.plan_char("\t"), [macos.KeyPress(48)])

    def test_text_uses_unicode_strings(self):
        for ch in "aA .,é€😀":
            self.assertEqual(macos.plan_char(ch), [macos.KeyPress(0, ch)])

    def test_send_char_posts_down_and_up_with_exact_unicode(self):
        cg, cf = FakeCG(), FakeCF()
        be = macos.MacBackend(cg=cg, cf=cf)
        be.send_char("é")
        self.assertEqual(len(cg.calls), 2)
        (tap1, down), (tap2, up) = cg.calls
        self.assertEqual((tap1, tap2), (0, 0))  # HID event tap
        self.assertTrue(down["down"])
        self.assertFalse(up["down"])
        for ev in (down, up):
            self.assertEqual(ev["text"], (1, [0xE9]))
            self.assertEqual(ev["flags"], 0)  # held modifiers must not leak into the text
        self.assertEqual(len(cf.released), 2)  # every event is released

    def test_emoji_is_posted_as_one_utf16_string(self):
        cg = FakeCG()
        macos.MacBackend(cg=cg, cf=FakeCF()).send_char("😀")
        self.assertEqual(cg.calls[0][1]["text"], (2, [0xD83D, 0xDE00]))

    def test_newline_and_tab_post_real_keycodes_without_text(self):
        cg = FakeCG()
        be = macos.MacBackend(cg=cg, cf=FakeCF())
        be.send_char("\n")
        be.send_char("\t")
        self.assertEqual([c[1]["keycode"] for c in cg.calls], [36, 36, 48, 48])
        self.assertTrue(all(c[1]["text"] is None for c in cg.calls))

    def test_failed_event_creation_raises(self):
        class NoEvents(FakeCG):
            def CGEventCreateKeyboardEvent(self, *a):
                return None

        with self.assertRaises(OSError):
            macos.MacBackend(cg=NoEvents(), cf=FakeCF()).send_char("a")

    def test_stop_keys_use_mac_keycodes(self):
        self.assertEqual(macos.KEYCODES["F8"], 100)
        self.assertEqual(macos.KEYCODES["Esc"], 53)
        self.assertEqual(len(set(macos.KEYCODES.values())), len(macos.KEYCODES))
        self.assertNotIn("Pause", macos.KEYCODES)  # no Pause key on Macs
        cg = FakeCG()
        be = macos.MacBackend(cg=cg, cf=FakeCF())
        self.assertFalse(be.is_stop_key_down("F8"))
        cg.keys_down = {100}
        self.assertTrue(be.is_stop_key_down("F8"))
        self.assertFalse(be.is_stop_key_down("bogus"))

    def test_permissions(self):
        be = macos.MacBackend(cg=FakeCG(trusted=False, listen=False), cf=FakeCF())
        self.assertEqual(be.permissions(), PermissionStatus(False, False))
        be = macos.MacBackend(cg=FakeCG(trusted=True, listen=False), cf=FakeCF())
        self.assertEqual(be.permissions(), PermissionStatus(True, False))
        old_macos = macos.MacBackend(cg=FakeCG(trusted=True, has_listen_api=False), cf=FakeCF())
        self.assertEqual(old_macos.permissions(), PermissionStatus(True, True))  # API missing -> assume ok

    def test_settings_urls_point_to_the_right_panes(self):
        self.assertIn("Privacy_Accessibility", macos.SETTINGS_URLS["accessibility"])
        self.assertIn("Privacy_ListenEvent", macos.SETTINGS_URLS["input_monitoring"])


    def test_backspace_is_the_mac_delete_key(self):
        self.assertEqual(macos.plan_backspace(), [macos.KeyPress(51)])
        cg = FakeCG()
        macos.MacBackend(cg=cg, cf=FakeCF()).send_backspace()
        self.assertEqual([(c[1]["keycode"], c[1]["down"], c[1]["text"]) for c in cg.calls],
                         [(51, True, None), (51, False, None)])
        self.assertNotEqual(macos.KVK_DELETE, windows.VK_BACK)       # different codes per OS

    def test_foreground_token_is_the_frontmost_app(self):
        be = macos.MacBackend(cg=FakeCG(), cf=FakeCF(), frontmost_pid=lambda: 4242)
        self.assertEqual(be.foreground_token(), 4242)
        be = macos.MacBackend(cg=FakeCG(), cf=FakeCF(), frontmost_pid=lambda: None)
        self.assertIsNone(be.foreground_token())              # unreadable -> the engine simply skips the check


class CrossPlatformTests(unittest.TestCase):
    def test_f8_is_available_and_default_everywhere(self):
        self.assertEqual(DEFAULT_STOP_KEY, "F8")
        for cls in (windows.WindowsBackend, macos.MacBackend, UnsupportedBackend):
            self.assertIn("F8", cls.stop_keys)

    def test_f8_codes_differ_between_systems(self):
        self.assertNotEqual(windows.VK_CODES["F8"], macos.KEYCODES["F8"])

    def test_both_backends_type_identical_text(self):
        """Whatever the OS, newline/tab become real keys and every other character is typed exactly."""
        def win_text():
            out = []
            for ch in SAMPLE:
                ev = windows.plan_char(ch)
                if ev[0].vk:
                    out.append({windows.VK_RETURN: "\n", windows.VK_TAB: "\t"}[ev[0].vk])
                else:
                    units = [e.scan for e in ev if not e.flags & windows.KEYEVENTF_KEYUP]
                    out.append(b"".join(u.to_bytes(2, "little") for u in units).decode("utf-16-le"))
            return "".join(out)

        def mac_text():
            out = []
            for ch in SAMPLE:
                for press in macos.plan_char(ch):
                    out.append({36: "\n", 48: "\t"}[press.keycode] if press.text is None else press.text)
            return "".join(out)

        self.assertEqual(win_text(), SAMPLE)
        self.assertEqual(mac_text(), SAMPLE)

    def test_permission_instructions_exist_in_both_languages(self):
        for table, word in ((EN, "Accessibility"), (ES, "Accesibilidad")):
            steps = " ".join(table[k] for k in ("perm_step1", "perm_step2", "perm_step3", "perm_step4"))
            self.assertIn(word, steps)
            self.assertIn("AutoTyper", steps)
        self.assertIn("Input Monitoring", EN["perm_input"])
        self.assertIn("Fn", EN["set_stop_key_mac"])
        self.assertIn("Fn", ES["set_stop_key_mac"])

    def test_structures_are_importable_on_any_os(self):
        self.assertGreater(ctypes.sizeof(windows.INPUT), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
