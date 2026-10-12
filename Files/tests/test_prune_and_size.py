"""Size optimization: which files stay in the bundle, the size report, and what the build config promises."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

import _path  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "installer"))

import prune  # noqa: E402
import size_report  # noqa: E402


class PruneRulesTests(unittest.TestCase):
    NEEDED = [
        # Windows
        "AutoTyper.exe", "python313.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll", "base_library.zip",
        "PySide6/Qt6Core.dll", "PySide6/Qt6Gui.dll", "PySide6/Qt6Widgets.dll", "PySide6/Qt6Svg.dll",
        "PySide6/QtCore.pyd", "PySide6/QtGui.pyd", "PySide6/QtWidgets.pyd", "PySide6/QtSvg.pyd",
        "PySide6/pyside6.abi3.dll", "shiboken6/Shiboken.pyd", "shiboken6/shiboken6.abi3.dll",
        "PySide6/plugins/platforms/qwindows.dll", "PySide6/plugins/styles/qmodernwindowsstyle.dll",
        "assets/icons/icon.png", "PySide6/Qt/plugins/platforms/qwindows.dll",
        # macOS
        "PySide6/Qt/lib/QtCore.framework/Versions/A/QtCore", "PySide6/Qt/lib/QtGui.framework/Versions/A/QtGui",
        "PySide6/Qt/lib/QtWidgets.framework/Versions/A/QtWidgets", "PySide6/Qt/lib/QtSvg.framework/Versions/A/QtSvg",
        "PySide6/Qt/plugins/platforms/libqcocoa.dylib", "PySide6/QtCore.abi3.so", "libpython3.12.dylib",
    ]
    UNNEEDED = [
        "PySide6/opengl32sw.dll", "PySide6/d3dcompiler_47.dll",                       # biggest wins on Windows
        "PySide6/Qt6Network.dll", "PySide6/Qt6Pdf.dll", "PySide6/Qt6Qml.dll", "PySide6/Qt6Quick.dll",
        "PySide6/Qt6OpenGL.dll", "PySide6/Qt6VirtualKeyboard.dll", "PySide6/Qt6QmlModels.dll",
        "PySide6/QtNetwork.pyd", "PySide6/QtOpenGL.pyd", "PySide6/QtQml.pyd",
        "PySide6/plugins/imageformats/qjpeg.dll", "PySide6/plugins/imageformats/qpdf.dll",
        "PySide6/plugins/iconengines/qsvgicon.dll", "PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll",
        "PySide6/plugins/generic/qtuiotouchplugin.dll", "PySide6/plugins/tls/qschannelbackend.dll",
        "PySide6/plugins/networkinformation/qnetworklistmanager.dll",
        "PySide6/translations/qtbase_de.qm", "PySide6/Qt/translations/qt_es.qm", "PySide6/Qt/qml/QtQuick/qmldir",
        "PySide6/QtCore.pyi",
        "PySide6/Qt/lib/QtNetwork.framework/Versions/A/QtNetwork", "PySide6/Qt/lib/QtPdf.framework/Versions/A/QtPdf",
        "PySide6/Qt/lib/QtOpenGL.framework/Versions/A/QtOpenGL", "PySide6/Qt/plugins/imageformats/libqjpeg.dylib",
        "PySide6/Qt/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.dylib",
    ]

    def test_everything_the_app_needs_is_kept(self):
        for name in self.NEEDED:
            self.assertTrue(prune.keep_entry(name), f"would wrongly drop: {name}")

    def test_unneeded_qt_parts_are_removed(self):
        for name in self.UNNEEDED:
            self.assertFalse(prune.keep_entry(name), f"would wrongly keep: {name}")

    def test_works_with_windows_style_paths(self):
        self.assertTrue(prune.keep_entry("PySide6\\plugins\\platforms\\qwindows.dll"))
        self.assertFalse(prune.keep_entry("PySide6\\plugins\\imageformats\\qjpeg.dll"))

    def test_prune_filters_a_toc_and_keeps_its_shape(self):
        toc = [("PySide6/Qt6Core.dll", "/x/Qt6Core.dll", "BINARY"), ("PySide6/opengl32sw.dll", "/x/o.dll", "BINARY")]
        self.assertEqual(prune.prune(toc), [toc[0]])

    def test_only_the_qt_modules_autotyper_imports_are_kept(self):
        self.assertEqual(prune.KEEP_QT_MODULES, {"core", "gui", "widgets", "svg"})
        import ast
        modules = set()
        for folder, _dirs, files in os.walk(os.path.join(ROOT, "src")):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(folder, name), encoding="utf-8") as fh:
                        for node in ast.walk(ast.parse(fh.read())):
                            if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").startswith("PySide6."):
                                modules.add(node.module.split(".")[1].lower().replace("qt", "", 1))
        self.assertTrue(modules <= prune.KEEP_QT_MODULES, f"the app imports Qt modules that would be removed: {modules}")

    def test_excluded_modules_are_not_imported_by_the_app(self):
        import ast
        imported = set()
        for folder, _dirs, files in os.walk(os.path.join(ROOT, "src")):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(folder, name), encoding="utf-8") as fh:
                        for node in ast.walk(ast.parse(fh.read())):
                            if isinstance(node, ast.Import):
                                imported |= {a.name.split(".")[0] for a in node.names}
                            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                                imported.add(node.module.split(".")[0])
        clash = imported & set(prune.EXCLUDE_MODULES)
        self.assertEqual(clash, set(), "the app imports a module the spec excludes")

    def test_upx_is_opt_in(self):
        spec = open(os.path.join(ROOT, "installer", "AutoTyper.spec"), encoding="utf-8").read()
        self.assertIn('UPX = os.environ.get("AUTOTYPER_UPX") == "1"', spec)
        self.assertNotIn("upx=True", spec)


class SizeReportTests(unittest.TestCase):
    def make_bundle(self, root, files):
        for rel, size in files.items():
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(b"0" * size)

    FILES = {"AutoTyper.exe": 3000, "_internal/python313.dll": 6000, "_internal/PySide6/Qt6Core.dll": 8000,
             "_internal/PySide6/opengl32sw.dll": 20000, "_internal/PySide6/plugins/platforms/qwindows.dll": 900,
             "_internal/PySide6/plugins/imageformats/qjpeg.dll": 500, "_internal/PySide6/translations/qtbase_de.qm": 100}

    def test_human_sizes(self):
        self.assertEqual(size_report.human(512), "512 B")
        self.assertEqual(size_report.human(2048), "2.0 KB")
        self.assertEqual(size_report.human(5 * 1024 * 1024), "5.0 MB")

    def test_report_lists_biggest_files_and_categories(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_bundle(d, self.FILES)
            text, data = size_report.report(d, top=3)
        self.assertEqual(data["total"], sum(self.FILES.values()))
        lines = text.splitlines()
        biggest = [l for l in lines if "opengl32sw.dll" in l]
        self.assertTrue(biggest)
        self.assertLess(lines.index(biggest[0]), lines.index([l for l in lines if "Qt6Core.dll" in l][0]))
        for name in ("Qt libraries", "Qt plugins", "Python runtime", "Qt translations"):
            self.assertIn(name, data["categories"])

    def test_symlinks_are_not_counted_twice(self):
        if not hasattr(os, "symlink"):
            self.skipTest("no symlinks")
        with tempfile.TemporaryDirectory() as d:
            self.make_bundle(d, {"a/file.bin": 1000})
            try:
                os.symlink(os.path.join(d, "a"), os.path.join(d, "link"))
            except OSError:
                self.skipTest("cannot create symlinks here")
            _text, data = size_report.report(d)
        self.assertEqual(data["total"], 1000)

    def test_before_after_comparison_shows_the_saving(self):
        with tempfile.TemporaryDirectory() as d:
            before_dir, after_dir = os.path.join(d, "b"), os.path.join(d, "a")
            self.make_bundle(before_dir, self.FILES)
            kept = {k: v for k, v in self.FILES.items() if prune.keep_entry(k)}
            self.make_bundle(after_dir, kept)
            b = size_report.report(before_dir)[1]
            a = size_report.report(after_dir)[1]
            path_b, path_a = os.path.join(d, "b.json"), os.path.join(d, "a.json")
            for path, data in ((path_b, b), (path_a, a)):
                with open(path, "w") as fh:
                    json.dump(data, fh)
            with open(path_b) as fb, open(path_a) as fa:
                text = size_report.compare(json.load(fb), json.load(fa))
        self.assertLess(a["total"], b["total"])
        self.assertIn("Qt libraries", text)
        self.assertIn("->", text)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_bundle(d, self.FILES)
            out = os.path.join(d, "after.json")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(size_report.main([d, "--top", "2", "--save", out]), 0)
            with open(out) as fh:
                self.assertTrue(json.load(fh)["total"] > 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(size_report.main([os.path.join(d, "missing")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
