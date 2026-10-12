# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe shared by Windows (AutoTyper.exe folder) and macOS (AutoTyper.app).
# Python, PySide6 and every other dependency are bundled, so end users install nothing else.
#
#   pyinstaller --noconfirm --clean --distpath build/dist --workpath build/work installer/AutoTyper.spec
#
# macOS: set AUTOTYPER_ARCH=universal2 to build for Intel + Apple Silicon (needs a universal2 Python).
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))        # the "Files" folder
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, SPECPATH)
from autotyper import __version__ as VERSION  # noqa: E402
import prune  # noqa: E402  (installer/prune.py: what is left out of the bundle to keep it small)

PRUNE = os.environ.get("AUTOTYPER_NO_PRUNE") != "1"      # AUTOTYPER_NO_PRUNE=1 -> keep everything
UPX = os.environ.get("AUTOTYPER_UPX") == "1"             # experimental, off by default

ICO = os.path.join(ROOT, "assets", "icons", "icon.ico")
ICNS = os.path.join(ROOT, "assets", "icons", "icon.icns")
PNG = os.path.join(ROOT, "assets", "icons", "icon.png")

# --- Windows version information shown in the file's Properties > Details tab -----------------
version_file = None
if sys.platform == "win32":
    parts = [int(p) for p in VERSION.split(".")] + [0, 0, 0, 0]
    tup = tuple(parts[:4])
    dotted = ".".join(str(p) for p in tup)
    work = os.path.join(ROOT, "build", "work")
    os.makedirs(work, exist_ok=True)
    version_file = os.path.join(work, "version_info.txt")
    with open(version_file, "w", encoding="utf-8") as fh:
        fh.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'AutoTyper'),
      StringStruct('FileDescription', 'AutoTyper'),
      StringStruct('FileVersion', '{dotted}'),
      StringStruct('InternalName', 'AutoTyper'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', 'AutoTyper.exe'),
      StringStruct('ProductName', 'AutoTyper'),
      StringStruct('ProductVersion', '{dotted}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[os.path.join(ROOT, "src")],
    binaries=[],
    datas=[(PNG, os.path.join("assets", "icons"))],
    hiddenimports=collect_submodules("autotyper") + ["PySide6.QtSvg"],
    excludes=(prune.EXCLUDE_MODULES + prune.EXCLUDE_QT) if PRUNE else ["tkinter", "unittest", "pytest"],
    noarchive=False,
)
if PRUNE:   # drop software OpenGL, Direct3D compiler, unused Qt libraries/plugins/translations
    a.binaries = prune.prune(a.binaries)
    a.datas = prune.prune(a.datas)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoTyper",
    console=False,                       # no console window, ever
    icon=ICO if sys.platform == "win32" else ICNS,
    version=version_file,
    target_arch=os.environ.get("AUTOTYPER_ARCH") or None,
    debug=False,
    strip=False,
    upx=UPX,
    upx_exclude=prune.UPX_EXCLUDE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=UPX,
    upx_exclude=prune.UPX_EXCLUDE,
    name="AutoTyper",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AutoTyper.app",
        icon=ICNS,
        bundle_identifier="com.autotyper.app",   # keep stable so macOS remembers the permissions
        version=VERSION,
        info_plist={
            "CFBundleName": "AutoTyper",
            "CFBundleDisplayName": "AutoTyper",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.productivity",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "MIT License",
        },
    )
