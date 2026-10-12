#!/usr/bin/env bash
# Builds the macOS release on a Mac:
#   AutoTyper/AutoTyper-macOS.dmg        (installer, next to the Files folder; with AUTOTYPER_ARCH=arm64|x86_64
#                                         it is named AutoTyper-macOS-<arch>.dmg so both can sit side by side)
#   Files/build/dist/AutoTyper.app       (the app itself)
#
# Run:  bash Files/installer/macos/build_macos.sh
#
# Optional environment variables:
#   CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"   real signing (default: ad-hoc)
#   NOTARY_PROFILE="my-profile"     notarize + staple the DMG (profile created with `xcrun notarytool store-credentials`)
#   AUTOTYPER_ARCH=universal2|arm64|x86_64   force the architecture (default: universal2 if Python allows it, else this Mac's)
#   SKIP_TESTS=1   SKIP_SELFTEST=1
#   AUTOTYPER_NO_PRUNE=1   build WITHOUT the size optimizations (to measure before/after)
#   DMG_FORMAT=ULMO|UDZO   disk-image compression (default ULMO = LZMA, smallest; needs macOS 10.15+)
set -euo pipefail

FILES="$(cd "$(dirname "$0")/../.." && pwd)"
REPO="$(cd "$FILES/.." && pwd)"
cd "$FILES"
step() { printf '\n==> %s\n' "$1"; }

command -v python3 >/dev/null || { echo "Python 3.10+ is required to BUILD the app (people who install it need nothing). Get it from https://www.python.org/downloads/macos/"; exit 1; }

step "Creating build environment"
python3 -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements-build.txt

VERSION="$(python -c "import sys; sys.path.insert(0,'src'); import autotyper; print(autotyper.__version__)")"
echo "Building AutoTyper $VERSION"

[ -f assets/icons/icon.icns ] || python assets/make_icons.py

# Intel + Apple Silicon: possible when this Python is a universal2 build (python.org installer)
USER_ARCH="${AUTOTYPER_ARCH:-}"        # only an architecture you ask for explicitly changes the file name
if [ -z "${AUTOTYPER_ARCH:-}" ]; then
  PYBIN="$(python -c 'import sys; print(sys.executable)')"
  if lipo -archs "$PYBIN" 2>/dev/null | grep -q "x86_64" && lipo -archs "$PYBIN" 2>/dev/null | grep -q "arm64"; then
    AUTOTYPER_ARCH="universal2"
  else
    AUTOTYPER_ARCH="$(uname -m)"
    echo "NOTE: this Python is not universal2, so the app is built only for $AUTOTYPER_ARCH."
  fi
fi
export AUTOTYPER_ARCH
echo "Target architecture: $AUTOTYPER_ARCH"
# A single-architecture build gets the architecture in the file name; universal2 keeps the plain name
case "$USER_ARCH" in ""|universal2) SUFFIX="" ;; *) SUFFIX="-$USER_ARCH" ;; esac

if [ "${SKIP_TESTS:-0}" != "1" ]; then
  step "Running tests"
  QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
fi

step "Packaging the app with PyInstaller (bundles Python + PySide6)"
pyinstaller --noconfirm --clean --distpath build/dist --workpath build/work installer/AutoTyper.spec
APP="$FILES/build/dist/AutoTyper.app"
[ -x "$APP/Contents/MacOS/AutoTyper" ] || { echo "AutoTyper.app was not created"; exit 1; }
echo "Architectures in the app: $(lipo -archs "$APP/Contents/MacOS/AutoTyper" 2>/dev/null || echo unknown)"

step "Size of the packaged app (biggest files first)"
TAG=after; [ "${AUTOTYPER_NO_PRUNE:-0}" = "1" ] && TAG=before
python installer/size_report.py "$APP" --top 15 --save "build/size-$TAG.json"
if [ -f build/size-before.json ] && [ -f build/size-after.json ]; then
  echo; echo "Before / after optimization:"; python installer/size_report.py --compare build/size-before.json build/size-after.json
fi

step "Signing"
IDENTITY="${CODESIGN_IDENTITY:--}"
if [ "$IDENTITY" = "-" ]; then
  echo "Ad-hoc signature (fine for your own Mac; to share it, sign with CODESIGN_IDENTITY - see the README)"
  codesign --force --deep --sign - "$APP"
else
  codesign --force --deep --options runtime --timestamp --sign "$IDENTITY" "$APP"
fi
codesign --verify --deep --strict "$APP" && echo "Signature OK"

if [ "${SKIP_SELFTEST:-0}" != "1" ]; then
  step "Checking that the packaged app contains all its dependencies"
  "$APP/Contents/MacOS/AutoTyper" --self-test || { cat "${TMPDIR:-/tmp}/AutoTyper-selftest.log" 2>/dev/null || true; echo "Self-test of the packaged app failed. To check whether the size pruning is the cause, run again with AUTOTYPER_NO_PRUNE=1."; exit 1; }
  echo "Self-test passed"
fi

step "Creating the .dmg"
DMG_NAME="AutoTyper-macOS${SUFFIX}.dmg"
DMG="$FILES/build/$DMG_NAME"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"      # drag AutoTyper onto Applications
rm -f "$DMG"
# ULMO (LZMA) gives the smallest image; fall back to maximum-level zlib if this Mac cannot make it
if ! hdiutil create -volname "AutoTyper" -srcfolder "$STAGE" -ov -format "${DMG_FORMAT:-ULMO}" "$DMG"; then
  echo "ULMO not available, using UDZO (zlib level 9)"
  rm -f "$DMG"
  hdiutil create -volname "AutoTyper" -srcfolder "$STAGE" -ov -format UDZO -imagekey zlib-level=9 "$DMG"
fi
rm -rf "$STAGE"
if [ "$IDENTITY" != "-" ]; then
  codesign --force --timestamp --sign "$IDENTITY" "$DMG"
fi

if [ -n "${NOTARY_PROFILE:-}" ] && [ "$IDENTITY" != "-" ]; then
  step "Notarizing (this can take a few minutes)"
  xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi

cp "$DMG" "$REPO/$DMG_NAME"
SIZE_MB="$(python -c "import os,sys; print(round(os.path.getsize(sys.argv[1])/1048576,1))" "$DMG")"
printf '\nDONE.\n  DMG: %s\n  App: %s\n' "$REPO/$DMG_NAME" "$APP"
echo "Installer size: ${SIZE_MB} MB (architecture: ${AUTOTYPER_ARCH}; target: under 25 MB)"
