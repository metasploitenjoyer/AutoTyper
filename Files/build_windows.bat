@echo off
REM Double-click to build AutoTyper-SetupWindows.exe (installer) and the portable ZIP.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\windows\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Build FAILED - read the messages above.
) else (
  echo.
  echo Build finished. AutoTyper-SetupWindows.exe is in the AutoTyper folder.
)
pause
