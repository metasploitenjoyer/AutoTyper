"""Static checks that the installers will contain every dependency and are wired correctly."""

import ast
import os
import re
import struct
import sys
import unittest

import _path  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the "Files" folder
REPO = os.path.dirname(ROOT)                                        # the "AutoTyper" folder


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def read_repo(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def read_bytes(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        return fh.read()


def python_files():
    for folder, _dirs, files in os.walk(os.path.join(ROOT, "src")):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(folder, name)
    yield os.path.join(ROOT, "main.py")


class DependencyTests(unittest.TestCase):
    def test_every_third_party_import_is_in_requirements(self):
        third_party = set()
        for path in python_files():
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                third_party |= {n for n in names if n not in sys.stdlib_module_names and n != "autotyper"}
        requirements = {re.split(r"[<>=!~\[ ]", line.strip())[0].lower()
                        for line in read("requirements.txt").splitlines()
                        if line.strip() and not line.startswith("#")}
        if "pyside6-essentials" in requirements:      # the PySide6 *Essentials* package provides `import PySide6`
            requirements.add("pyside6")
        self.assertEqual({n.lower() for n in third_party} - requirements, set(),
                         "imported but missing from requirements.txt")
        self.assertEqual(third_party, {"PySide6"})  # no keyboard package needed: native APIs are used
        # only the smaller "Essentials" Qt package is needed (QtCore/Gui/Widgets/Svg), not the full PySide6
        self.assertIn("pyside6-essentials", requirements)
        self.assertNotIn("pyside6", {r.lower() for r in read("requirements.txt").split() if r.lower() == "pyside6"})

    def test_build_requirements(self):
        build = read("requirements-build.txt")
        self.assertIn("-r requirements.txt", build)
        self.assertIn("pyinstaller", build.lower())

    def test_no_python_needed_for_users_everything_is_bundled(self):
        spec = read("installer", "AutoTyper.spec")
        for needle in ("collect_submodules(\"autotyper\")", "PySide6.QtSvg", "icon.png", "COLLECT(",
                       "console=False", "BUNDLE(", "bundle_identifier=\"com.autotyper.app\"",
                       "NSHighResolutionCapable", "prune.prune(a.binaries)", "EXCLUDE_QT", "AUTOTYPER_NO_PRUNE",
                       "AUTOTYPER_UPX", "upx=UPX"):
            self.assertIn(needle, spec)


class WindowsInstallerTests(unittest.TestCase):
    def setUp(self):
        self.iss = read("installer", "windows", "AutoTyper.iss")
        self.ps1 = read("installer", "windows", "build_windows.ps1")

    def test_installer_creates_desktop_and_start_menu_shortcuts(self):
        self.assertIn("[Icons]", self.iss)
        self.assertIn('Name: "{group}\\{#AppName}"', self.iss)                 # Start menu
        self.assertRegex(self.iss, r'Name: "\{autodesktop\}\\\{#AppName\}".*Tasks: desktopicon')  # Desktop
        self.assertIn('Name: "desktopicon"', self.iss)
        self.assertNotIn("unchecked", self.iss)                                  # desktop icon ticked by default

    def test_installer_ships_the_whole_bundle(self):
        self.assertIn('Source: "{#SourceDir}\\*"', self.iss)
        self.assertIn("recursesubdirs", self.iss)
        self.assertIn('#define SourceDir "..\\..\\build\\dist\\AutoTyper"', self.iss)
        self.assertIn("SetupIconFile=..\\..\\assets\\icons\\icon.ico", self.iss)
        self.assertIn("OutputBaseFilename=AutoTyper-SetupWindows\n", self.iss)   # final name: AutoTyper-SetupWindows.exe
        self.assertIn("Compression=lzma2/ultra64", self.iss)               # strongest compression
        self.assertIn("SolidCompression=yes", self.iss)
        self.assertIn("UninstallDisplayIcon", self.iss)
        self.assertIn("LicenseFile=", self.iss)
        self.assertIn("VersionInfoVersion={#AppVersion}", self.iss)
        self.assertIn("AppMutex=", self.iss)                                # detects a running AutoTyper
        self.assertIn("AppId={{", self.iss)                                 # same id -> upgrades in place

    def test_build_script_runs_every_step(self):
        for needle in ("requirements-build.txt", "unittest discover", "PyInstaller", "AutoTyper.spec",
                       "--self-test", "ISCC", "AutoTyper.iss", "/DAppVersion", "AutoTyper-Portable.zip",
                       'Join-Path $repo "AutoTyper-SetupWindows.exe"', "size_report.py", "AUTOTYPER_NO_PRUNE"):
            self.assertIn(needle, self.ps1)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "build_windows.bat")))   # double-click wrapper

    def test_icon_file_referenced_by_installer_exists(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "assets", "icons", "icon.ico")))


class MacInstallerTests(unittest.TestCase):
    def setUp(self):
        self.sh = read("installer", "macos", "build_macos.sh")

    def test_build_script_makes_app_and_dmg(self):
        for needle in ("requirements-build.txt", "unittest discover", "pyinstaller", "AutoTyper.spec",
                       "--self-test", "codesign", "hdiutil create", "ln -s /Applications",
                       "AutoTyper-macOS.dmg", "CODESIGN_IDENTITY", "notarytool", "stapler", "ULMO", "size_report.py",
                       "universal2", "AUTOTYPER_ARCH"):
            self.assertIn(needle, self.sh)

    def test_script_is_executable_and_strict(self):
        self.assertTrue(self.sh.startswith("#!/usr/bin/env bash"))   # (the exec bit is lost by zip tools; the README uses `bash script`)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "build_macos.sh")))     # wrapper next to the .bat
        self.assertIn("set -euo pipefail", self.sh)

    def test_workflow_builds_both_installers(self):
        wf = read_repo(".github", "workflows", "build-installers.yml")
        self.assertIn("windows-latest", wf)
        self.assertIn("macos-latest", wf)
        self.assertIn("build_windows.ps1", wf)
        self.assertIn("build_macos.sh", wf)
        self.assertIn("AutoTyper-SetupWindows.exe", wf)
        self.assertIn("gh release create", wf)                     # installers are published as Release assets


class AssetTests(unittest.TestCase):
    def test_png(self):
        data = read_bytes("assets", "icons", "icon.png")
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (512, 512))

    def test_ico_has_all_windows_sizes(self):
        data = read_bytes("assets", "icons", "icon.ico")
        reserved, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 6)
        sizes = set()
        for i in range(count):
            w, h, _c, _r, _planes, _bits, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
            sizes.add(w or 256)
            self.assertEqual(data[offset:offset + 8], b"\x89PNG\r\n\x1a\n")
            self.assertLessEqual(offset + length, len(data))
        self.assertTrue({16, 32, 48, 256} <= sizes)

    def test_icns_is_well_formed(self):
        data = read_bytes("assets", "icons", "icon.icns")
        self.assertEqual(data[:4], b"icns")
        self.assertEqual(struct.unpack(">I", data[4:8])[0], len(data))
        pos, kinds = 8, []
        while pos < len(data):
            tag, length = data[pos:pos + 4], struct.unpack(">I", data[pos + 4:pos + 8])[0]
            self.assertEqual(data[pos + 8:pos + 16], b"\x89PNG\r\n\x1a\n")
            kinds.append(tag)
            pos += length
        self.assertEqual(pos, len(data))
        self.assertIn(b"ic10", kinds)  # 1024px (Retina) icon

    def test_version_is_semver(self):
        from autotyper import __version__
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_project_layout(self):
        for item in ("main.py", "requirements.txt", "requirements-build.txt", "README.md", "CHANGELOG.md",
                     "build_windows.bat", "build_macos.sh", os.path.join("src", "autotyper", "engine.py"),
                     os.path.join("assets", "icons"), "tests", "installer", "build",
                     os.path.join("installer", "prune.py"), os.path.join("installer", "size_report.py")):
            self.assertTrue(os.path.exists(os.path.join(ROOT, item)), item)
        for item in ("LICENSE", "README.md", os.path.join(".github", "workflows", "build-installers.yml")):
            self.assertTrue(os.path.exists(os.path.join(REPO, item)), item)

    def test_no_fake_installers_are_shipped(self):
        """Installers only exist if they were really built: nothing pretends to be one."""
        for name in ("AutoTyper-SetupWindows.exe", "AutoTyper-macOS.dmg"):
            path = os.path.join(REPO, name)
            if os.path.exists(path):
                self.assertGreater(os.path.getsize(path), 5_000_000, f"{name} is too small to be a real installer")

    def test_gitignore_keeps_caches_and_build_output_out_of_the_release(self):
        ignore = read_repo(".gitignore")
        for needle in ("__pycache__/", ".venv", "Files/build/*", "!Files/build/.gitkeep",
                       "AutoTyper-SetupWindows.exe", "*.dmg", "*.exe"):   # installers go to GitHub Releases, not Git
            self.assertIn(needle, ignore)


if __name__ == "__main__":
    unittest.main(verbosity=2)
