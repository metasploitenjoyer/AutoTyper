# AutoTyper

Paste text, choose how long it should take, press **Start**, click into Google Docs, Word, Notepad,
TextEdit or any other text field during the 5-second countdown, and AutoTyper types the text for you
with a natural rhythm. **F8** or the **Stop** button stops it at once.

No internet connection, account, API key or AI service is needed. Windows and macOS.

> **Release status.** The installers (`AutoTyper-SetupWindows.exe`, `AutoTyper-macOS.dmg`) are **not included
> in this folder yet**: they can only be produced on Windows and on macOS. Everything needed to build
> them is here. See [What has been verified](#what-has-been-verified) for exactly what was and was not tested.

---

## Install

### Windows 10 / 11
1. Run **`AutoTyper-SetupWindows.exe`** and follow the wizard (Next, Install, Finish).
2. It adds a Start Menu entry and, if you leave the box ticked, a desktop shortcut. No Python needed.
3. Installing a newer version over an old one upgrades it in place. If AutoTyper is running, the
   installer asks you to close it.

*Portable version:* unzip **`AutoTyper-Portable.zip`** anywhere and run `AutoTyper.exe` (no install,
no shortcuts, no uninstaller).

First run: Windows SmartScreen may say "Windows protected your PC" because the installer is not signed
with a paid certificate. Click **More info → Run anyway**.

### macOS 11 or newer (Intel and Apple Silicon)
1. Open **`AutoTyper-macOS.dmg`** and drag **AutoTyper** onto **Applications**.
2. Open AutoTyper from Applications. If macOS says it cannot verify the developer, right-click the app →
   **Open** → **Open** (only needed the first time, for builds that are not notarized).
3. Allow typing: see [Permissions on macOS](#permissions-on-macos).

---

## Use it

1. **Typing** tab: paste your text, pick a duration (30 s … 10 min or custom), press **Start**.
2. During the countdown, click into the app and the exact text field where the text should appear.
3. Watch the status, progress, elapsed and remaining time. **Pause** / **Resume** and **Stop** are always available.
4. Stop at any moment with **F8** (default) or the Stop button. Pause/resume with **F9** (default).

### Humanization tab
Optional natural rhythm: uneven keystrokes, pauses after words, punctuation, sentences and paragraphs,
and occasional thinking pauses.
- **Style:** *Steady*, *Natural*, *Slow & Thoughtful*.
- **Intensity:** *Low*, *Medium*, *High*, or *Custom* (sliders for variation, pauses and thinking pauses).
- Switched off = perfectly even speed. All delays are bounded, and the total time you chose is always respected.

### Corrections tab
Optional simulated typos. AutoTyper types a wrong letter (neighbouring key, swapped letters or a doubled
letter), "notices" after a delay, presses Backspace **only for the characters that belong to that mistake**
and types the right ones. Frequency and correction delay are adjustable.
- The text in the editor is **never** modified.
- Text that already exists in your document is **never** deleted.
- Corrections stop immediately if the active window changes or a key press fails.
- If you stop with the Stop *button* while a typo is on screen, up to a few extra letters can remain
  (clicking the button makes AutoTyper the active window, so no keys can be sent to your document).
  Stopping with the keyboard shortcut cleans them up first.

### Settings tab
Default duration, stop shortcut, pause shortcut, "stop if the active window changes", theme
(system / light / dark), keep window on top, language (English / Español). Settings are saved automatically.

### Safety behaviour
- Text is never typed into AutoTyper itself. If AutoTyper becomes the active window while typing, it
  **pauses**; press Resume, then click back into your app.
- If the active window changes (for example you Alt-Tab away), typing **stops**. To move to another document
  on purpose, press Pause first, switch, then Resume.

---

## Permissions

AutoTyper only uses the same keyboard input any program may send, and only after the operating system
allows it. It never tries to bypass OS security.

### Permissions on macOS
macOS blocks apps from typing into other apps until you allow it. AutoTyper shows these steps inside the app:
1. Click **Open System Settings** (or open it yourself).
2. **Privacy & Security → Accessibility** → switch **AutoTyper** on (use **+** to add it from Applications if it is not listed).
3. Back in AutoTyper, click **Check again**.

Recommended: also allow AutoTyper under **Privacy & Security → Input Monitoring**, so the stop and pause shortcuts
are detected while another app is active.

Notes:
- If AutoTyper is already switched on but typing still does nothing (this can happen after an update), select it in the list,
  remove it with **−**, add it again and restart AutoTyper.
- If you run from source (`python main.py`), grant the permission to **Terminal** (or your editor), not AutoTyper.
- On many Macs **F8** is a media key: use **Fn+F8**, enable "Use F1, F2, etc. keys as standard function keys" in
  System Settings → Keyboard, or choose another stop key (for example **Esc**) in Settings.
- Detecting the active app uses the system's Objective-C runtime. If it cannot be read, AutoTyper keeps working but the
  "stop if the active window changes" safeguard is inactive.

### Permissions on Windows
No special permission is needed. Windows does not let a normal program type into an app that runs **as administrator**;
if the target app does, run AutoTyper as administrator too.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Nothing is typed (Windows) | The target app may run as administrator: start AutoTyper as administrator. |
| Nothing is typed (macOS) | Enable Accessibility (see above), restart AutoTyper. |
| "AutoTyper was the active window" | After pressing Start, click into your document before the countdown ends. |
| F8 does nothing on a Mac | Use Fn+F8, change the stop key in Settings, or allow Input Monitoring. The Stop button always works. |
| Typing stopped by itself | The active window changed. Keep the target window in front, or press Pause before switching. |
| Characters are missing | The speed is too high for that app. Choose a longer duration (AutoTyper warns above about 20 characters/second). |
| Google Docs changes the text | Docs reacts to typing (automatic lists, smart quotes): turn it off in *Tools → Preferences*. |
| Windows SmartScreen / macOS Gatekeeper warning | The app is not signed/notarized; see the first-run steps above, or sign it (below). |
| Installer build fails the self-test | The details are in `AutoTyper-selftest.log` in your temp folder. |

---

## Uninstall

**Windows installer:** Start Menu → *AutoTyper* → *Uninstall AutoTyper*, or *Settings → Apps → Installed apps → AutoTyper → Uninstall*.
Your settings are kept in `%APPDATA%\AutoTyper`; delete that folder to remove them too.
**Windows portable:** delete the folder.

**macOS:** drag **AutoTyper** from Applications to the Trash. Optionally remove it from *Privacy & Security → Accessibility /
Input Monitoring* and delete `~/Library/Application Support/AutoTyper`.

---

## Develop and test

Python 3.10 or newer.

```bash
# Windows                              # macOS
python -m venv .venv                   python3 -m venv .venv
.venv\Scripts\activate                 source .venv/bin/activate
pip install -r requirements.txt        pip install -r requirements.txt
python main.py                         python main.py

python -m unittest discover -s tests -v        # run all tests (from the Files folder)
```

The logic tests use a mock keyboard and a fake text field, so they never type into real applications. The window tests
(`test_ui_smoke.py`) run headless when PySide6 is installed and are skipped automatically otherwise.

## Publish the installers (GitHub Releases, not Git)

Installer files are large binaries and are listed in `.gitignore`: keep them out of the repository and attach them to a Release:
```
gh release create v1.0.0 AutoTyper-SetupWindows.exe AutoTyper-macOS.dmg --title "AutoTyper 1.0.0" --notes "First release"
```
Pushing a tag such as `v1.0.0` to GitHub also builds both installers in the cloud and attaches them to the Release automatically
(`.github/workflows/build-installers.yml`; not yet tested).

## Build the installers

Building needs Python 3.10+ (people who *install* AutoTyper need nothing).

| Goal | Run | Result |
|---|---|---|
| Windows installer + portable ZIP | double-click `Files\build_windows.bat` | `AutoTyper\AutoTyper-SetupWindows.exe`, `Files\build\AutoTyper-Portable.zip` |
| macOS app + DMG | `bash Files/build_macos.sh` | `AutoTyper/AutoTyper-macOS.dmg`, `Files/build/dist/AutoTyper.app` |
| Both, in the cloud | GitHub → Actions → *Build installers* → Run workflow | downloadable artifacts |

Each script creates a build environment, installs `requirements-build.txt`, runs the tests, packages the app with PyInstaller,
**runs the packaged app's `--self-test`** (checks that Qt, plugins, icons and every module are really inside the package), and
then creates the installer. Windows also needs [Inno Setup 6](https://jrsoftware.org/isdl.php) (the script installs it with `winget`
if it can). Set `SKIP_TESTS=1` / `SKIP_SELFTEST=1` to skip those steps.

**Intel + Apple Silicon:** the macOS script builds a *universal2* app when the Python used to build is a universal2 build
(the installer from python.org is). Otherwise it builds for the Mac you run it on and says so. Check with
`lipo -archs Files/build/dist/AutoTyper.app/Contents/MacOS/AutoTyper`.

### Signing and notarization
Unsigned apps work, but show warnings. To remove them:

- **macOS** needs an Apple Developer Program membership (paid) and a *Developer ID Application* certificate.
  ```bash
  xcrun notarytool store-credentials "autotyper" --apple-id YOU@EXAMPLE.COM --team-id TEAMID --password APP-SPECIFIC-PASSWORD
  CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" NOTARY_PROFILE="autotyper" bash Files/build_macos.sh
  ```
  The script signs the app with the hardened runtime, signs and notarizes the DMG and staples the ticket. With the default
  ad-hoc signature, macOS may ask again for the Accessibility permission after each rebuild.
- **Windows** needs a code-signing certificate (an EV certificate gives immediate SmartScreen reputation). Sign
  `build\dist\AutoTyper\AutoTyper.exe` before compiling the installer, and `AutoTyper-SetupWindows.exe` afterwards, with `signtool sign`.

## Installer size

Goal: each installer **under 25 MB** (ideally 22-24 MB) without removing any feature.

What the build does to stay small (all of it can be switched off with `AUTOTYPER_NO_PRUNE=1`):
- Installs only **PySide6-Essentials** and bundles only the four Qt modules AutoTyper uses: Core, Gui, Widgets, Svg.
- Leaves out what PySide6 would otherwise add: the software OpenGL renderer (`opengl32sw.dll`) and the Direct3D compiler
  (`d3dcompiler_47.dll`) on Windows, Qt Network / PDF / QML / Quick / OpenGL, all Qt plugins except the platform plugin and the
  styles, Qt's own translations, and unused standard-library modules (rules in `installer/prune.py`).
- Windows installer: Inno Setup `lzma2/ultra64`, solid compression. macOS disk image: `ULMO` (LZMA) instead of the default zlib.
- UPX is **off** by default: Qt libraries often break when packed, antivirus tools dislike it, and the installer already compresses.
  Try it with `AUTOTYPER_UPX=1` only if you want to experiment.

Every build prints a size report (biggest files, totals by category) and the final installer size. To see before and after:
```
set AUTOTYPER_NO_PRUNE=1          (Windows)   /   AUTOTYPER_NO_PRUNE=1 bash Files/build_macos.sh   (macOS)
Files\build_windows.bat           -> saves Files\build\size-before.json
set AUTOTYPER_NO_PRUNE=            (clear it)
Files\build_windows.bat           -> saves size-after.json and prints "Before / after optimization"
```
The packaged app is also checked with `AutoTyper --self-test`, which starts the real window and types (with simulated typos, and a Stop test)
into a fake keyboard, so a wrongly removed library shows up at build time instead of for your users.

**Is 25 MB realistic?** *Windows:* very likely. The previous installer was 32.9 MB, and the removed parts (about 20 MB of software OpenGL and
4 MB of Direct3D compiler before compression, plus unused Qt libraries and plugins) are the largest items in a default PySide6 bundle.
*macOS:* probably only for a **single-architecture** build (Apple Silicon or Intel); a **universal2** app contains every Qt library twice and
will most likely stay above 25 MB. Build with `AUTOTYPER_ARCH=arm64` (or `x86_64`) to get `AutoTyper-macOS-arm64.dmg`. These are estimates, not
measurements: see *What has been verified*.

## Project layout

```
AutoTyper/
├── AutoTyper-SetupWindows.exe        (created by the Windows build)
├── AutoTyper-macOS.dmg        (created by the macOS build)
├── LICENSE
├── .github/workflows/         cloud build of both installers
└── Files/
    ├── main.py                entry point
    ├── src/autotyper/
    │   ├── engine.py            session: countdown, timing, pause/resume, stop, safety checks
    │   ├── plan.py              typing plan: timed steps, simulated typos and corrections
    │   ├── humanize.py          rhythm profiles (styles, levels, bounds)
    │   ├── system/              keyboard input per OS: windows.py (SendInput), macos.py (Quartz)
    │   ├── settings.py i18n.py  saved preferences, English/Spanish texts
    │   └── ui/                  Qt interface: tabs, theme, icons, permission panel
    ├── assets/icons/          app icon (png / ico / icns) and assets/make_icons.py
    ├── tests/                 automated tests
    ├── installer/             AutoTyper.spec (PyInstaller), windows/ (Inno Setup + script), macos/ (script)
    ├── build/                 generated build output (not part of the release)
    ├── requirements.txt  requirements-build.txt
    ├── build_windows.bat  build_macos.sh
    ├── README.md  CHANGELOG.md
```

## What has been verified

Verified in the development environment (Linux, Python 3.12, no Windows/macOS, no PySide6, no PyInstaller, no Inno Setup, no internet):
- **Automated logic tests** (173 tests, 16 skipped): timing, text handling, duration presets, humanization, simulated typos and corrections
  against a fake text field, Stop, F8-style stop, Pause/Resume, focus-change stop, invalid settings, Windows and macOS key events,
  settings, translations, packaging files, **the pruning rules** (what stays in / goes out of the bundle) and **the size-report tool**.
- The UI code and the packaged-app self-check were executed against a stand-in for PySide6 to catch coding mistakes.

Verified on a real Windows PC (by the project owner, earlier versions): the tests including the window tests, the build, and the installer
(32.9 MB before this optimization).

**Not verified; must be checked on the real systems:**
- **Installer sizes after this optimization.** No installer could be built here, so no new size was measured on either platform.
- That the pruned bundle starts and works (the build runs the packaged-app self-test; run it on Windows and macOS).
- Real keystrokes on Windows and macOS in Google Docs, Word, Notepad and TextEdit; the macOS permission flow and Fn/F8 behaviour.
- PyInstaller packaging, Inno Setup, the `.dmg`, universal2, signing, notarization, the portable ZIP, UPX.
- Installing, upgrading and uninstalling the Windows installer.

Licensed under the MIT License (see `LICENSE`).
