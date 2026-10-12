; Inno Setup script: builds the Windows installer  AutoTyper-SetupWindows.exe
; Compile with:  ISCC /DAppVersion=1.0.0 AutoTyper.iss      (build_windows.ps1 does this for you)
; Input : ..\..\build\dist\AutoTyper   (PyInstaller output)
; Output: ..\..\build\AutoTyper-SetupWindows.exe  (the build script then copies it next to the Files folder)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "AutoTyper"
#define AppExe "AutoTyper.exe"
#define SourceDir "..\..\build\dist\AutoTyper"

[Setup]
; The same AppId on every release = a new version upgrades the old one in place.
AppId={{B6C3E1F4-5A0D-4C8B-9E27-7D1A4F3C2B90}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright=MIT License
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\..\build
OutputBaseFilename=AutoTyper-SetupWindows
SetupIconFile=..\..\assets\icons\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=..\..\..\LICENSE
; Smallest installer: LZMA2 at its strongest setting, all files compressed together as one solid block
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
; Next / Install / Finish wizard. Installs for the current user without asking for administrator
; rights; a dialog lets people choose "for all users" instead.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; An already-running AutoTyper (it holds this mutex) is detected and closed or the user is asked to close it.
AppMutex=AutoTyper.SingleInstance
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
; Offered (and ticked) by default; the user can untick it.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Settings live in %APPDATA%\AutoTyper and are kept on purpose; delete that folder to remove them too.
Type: filesandordirs; Name: "{app}"
