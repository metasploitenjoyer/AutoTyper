# Changelog

## Unreleased - smaller installers
- Bundle only the Qt modules the app uses (Core, Gui, Widgets, Svg) and drop software OpenGL, the Direct3D compiler, Network/PDF/QML/Quick,
  unused Qt plugins and translations, and unused standard-library modules. `AUTOTYPER_NO_PRUNE=1` turns this off.
- Depend on `PySide6-Essentials` instead of the full `PySide6`.
- Windows installer renamed `AutoTyper-SetupWindows.exe`; Inno Setup `lzma2/ultra64`. macOS DMG uses LZMA (`ULMO`) with a zlib fallback;
  `AUTOTYPER_ARCH=arm64|x86_64` builds a single-architecture `AutoTyper-macOS-<arch>.dmg`.
- Size report after every build (`installer/size_report.py`) with before/after comparison; installer size printed at the end.
- The packaged-app self-test now starts the real window and types into a fake keyboard (with typos and a Stop test).
- UPX is optional and off by default (`AUTOTYPER_UPX=1`).
- Release workflow attaches the installers to a GitHub Release on version tags; installers stay out of Git.

## 1.0.0

### New
- **Humanize Typing**: optional natural rhythm with bounded random delays, pauses after words,
  punctuation, sentences and paragraphs, and occasional thinking pauses.
  Styles: Steady, Natural, Slow & Thoughtful. Intensity: Low, Medium, High, Custom.
- **Simulate typos & corrections**: types a wrong letter (neighbouring key, swapped letters or a
  doubled letter), waits, backspaces only the characters that belong to the mistake and types the
  right ones. The editor text is never modified and existing text in the destination is never deleted.
- **Pause / Resume** (button and global shortcut) with a short countdown to click back into the app.
- **Safety**: typing stops if the active window changes; typing never goes into AutoTyper itself
  (it pauses instead); a failed correction stops everything immediately.
- Elapsed time and estimated remaining time, tabs for Typing / Humanization / Corrections / Settings,
  preferences saved between sessions, English and Spanish interface.
- New project layout: installers at the top level, everything else inside `Files/`.

### Packaging
- Windows: Inno Setup installer (Next / Install / Finish, Start Menu and optional desktop shortcut,
  uninstaller, version information, upgrades in place) plus a portable ZIP.
- macOS: `.app` bundle in a drag-to-Applications `.dmg`, universal2 (Intel + Apple Silicon) when the
  build Python allows it, optional signing and notarization.
- Both packages are self-tested (`AutoTyper --self-test`) at build time.

### Changed
- Keyboard input is implemented natively per platform (Windows `SendInput`, macOS Quartz events);
  no keyboard automation package is required.
