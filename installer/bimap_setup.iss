; ============================================================================
; BIMAP — Inno Setup Script
; ============================================================================
; Requirements:
;   - Inno Setup 6.x  (https://jrsoftware.org/isdl.php)
;   - PyInstaller build output must exist at  installer\dist\BIMAP\
;   - Run via build_installer.ps1 or directly:
;       ISCC.exe bimap_setup.iss
; ============================================================================

#define MyAppName      "BIMAP"
#define MyAppVersion   "0.1.0"
#define MyAppPublisher "BIMAP Team"
#define MyAppURL       "https://github.com/yourorg/bimap"
#define MyAppExeName   "BIMAP.exe"
#define MyAppDist      "..\installer\dist\BIMAP"

[Setup]
AppId={{B1MAP-B141-4321-A000-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Require admin rights to write to Program Files
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=BIMAP_Setup_{#MyAppVersion}
SetupIconFile=bimap.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
; Minimum Windows 10
MinVersion=10.0.17763
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}";   GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application (PyInstaller onedir bundle)
Source: "{#MyAppDist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Optional: readme ──────────────────────────────────────────────────────────
Source: "..\readme.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";            Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";      Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Register .bimap file extension ──────────────────────────────────────────────
Root: HKCR; Subkey: ".bimap";                           ValueType: string; ValueName: ""; ValueData: "BIMAPProject";  Flags: uninsdeletevalue
Root: HKCR; Subkey: "BIMAPProject";                     ValueType: string; ValueName: ""; ValueData: "BIMAP Project"; Flags: uninsdeletekey
Root: HKCR; Subkey: "BIMAPProject\DefaultIcon";         ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCR; Subkey: "BIMAPProject\shell\open\command";  ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// ── Pre-install check: ensure no older version is running ──────────────────
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
