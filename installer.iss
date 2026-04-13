; Inno Setup 6 script — build IPS.exe first: pyinstaller ips_app.spec
; Compile this script with ISCC.exe (Inno Setup Compiler). Output: dist\installer\

#define MyAppName "IPS Estimating"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "IPS"
#define MyAppExeName "IPS.exe"

[Setup]
AppId={{A7B8C9D0-E1F2-3456-789A-BCDEF0123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist\installer
OutputBaseFilename=IPS_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=no
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
#if FileExists(AddBackslash(SourcePath) + "IPS_icon.ico")
SetupIconFile=IPS_icon.ico
#elif FileExists(AddBackslash(SourcePath) + "assets\ips_logo_round.ico")
SetupIconFile=assets\ips_logo_round.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
