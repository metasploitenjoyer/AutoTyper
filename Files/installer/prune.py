"""
Decides which files of the PyInstaller bundle are kept.  Used by AutoTyper.spec.

AutoTyper only uses Qt Core, Gui, Widgets and Svg, the platform plugin (qwindows /
qcocoa) and the built-in "Fusion" style. Everything else that PySide6 drags into a
bundle (software OpenGL, Direct3D compiler, Network, PDF, QML/Quick, image-format
plugins, translations, ...) only makes the installer bigger.

This is plain Python so it can be unit-tested on any system. Set AUTOTYPER_NO_PRUNE=1
when building to keep everything (useful to measure the size before/after, or to
check whether a problem is caused by pruning).
"""

KEEP_QT_MODULES = {"core", "gui", "widgets", "svg"}
KEEP_PLUGIN_DIRS = {"platforms", "styles"}
DROP_FILENAMES = {"opengl32sw.dll", "d3dcompiler_47.dll", "dxcompiler.dll", "dxil.dll"}
DROP_SUFFIXES = (".qm", ".pyi", ".qmltypes", ".qmlc")
DROP_QT_DIRS = ("translations", "qml", "metatypes", "resources", "lupdate")

# Standard-library and tool modules AutoTyper never imports
EXCLUDE_MODULES = [
    "tkinter", "unittest", "pytest", "pydoc", "doctest", "test", "distutils", "setuptools",
    "pkg_resources", "pip", "sqlite3", "ssl", "_ssl", "ftplib", "smtplib", "imaplib", "poplib",
    "xmlrpc", "curses", "lib2to3", "idlelib", "turtle", "wsgiref",
]
# Qt modules that PySide6 offers but AutoTyper never imports
EXCLUDE_QT = [
    "PySide6." + name for name in (
        "QtNetwork", "QtOpenGL", "QtOpenGLWidgets", "QtQml", "QtQuick", "QtQuickWidgets", "QtPdf",
        "QtPdfWidgets", "QtPrintSupport", "QtSql", "QtTest", "QtXml", "QtDBus", "QtConcurrent",
        "QtSvgWidgets", "QtHelp", "QtDesigner", "QtUiTools", "QtMultimedia", "QtMultimediaWidgets",
        "QtWebEngineCore", "QtWebEngineWidgets", "QtWebChannel", "QtWebSockets", "Qt3DCore",
        "QtCharts", "QtDataVisualization", "QtBluetooth", "QtNfc", "QtSensors", "QtPositioning",
        "QtSerialPort", "QtRemoteObjects", "QtScxml", "QtStateMachine", "QtTextToSpeech",
    )
]
# UPX is OFF by default: Qt libraries often break when packed, antivirus tools dislike it,
# and the installer compresses the files anyway. Set AUTOTYPER_UPX=1 to experiment.
UPX_EXCLUDE = ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "python*.dll", "qwindows.dll",
               "Qt6*.dll", "*.pyd"]


def _qt_module(stem):
    """'qt6core' -> 'core', 'QtNetwork' -> 'network', 'libQt6Gui' -> 'gui', anything else -> None."""
    s = stem.lower()
    if s.startswith("lib"):
        s = s[3:]
    for prefix in ("qt6", "qt"):
        if s.startswith(prefix):
            rest = s[len(prefix):]
            return rest or None
    return None


def keep_entry(name):
    """True if the bundle entry (its destination path inside the bundle) should be kept."""
    p = "/" + name.replace("\\", "/").lower().lstrip("/")
    base = p.rsplit("/", 1)[-1]
    if base in DROP_FILENAMES or p.endswith(DROP_SUFFIXES):
        return False
    qt_path = "/qt" in p or "pyside6" in p
    if qt_path and any(f"/{d}/" in p for d in DROP_QT_DIRS):
        return False
    if "/plugins/" in p:                                   # Qt plugins: only the platform + styles
        sub = p.split("/plugins/", 1)[1].split("/", 1)[0]
        if sub not in KEEP_PLUGIN_DIRS:
            return False
    for segment in p.split("/"):                           # Qt modules: only Core, Gui, Widgets, Svg
        module = _qt_module(segment.split(".")[0])
        if module and module not in KEEP_QT_MODULES:
            return False
    return True


def prune(toc):
    """Filter a PyInstaller TOC (list of (dest_name, src_name, typecode))."""
    return [entry for entry in toc if keep_entry(entry[0])]
