#ifdef ProductionBuild
  #define AppName "Anything Plays"
#else
  #define AppName "Anything Plays 3.0 Preview"
#endif
#ifndef AppVersion
  #define AppVersion "3.0.0-alpha.1"
#endif
[Setup]
#ifdef ProductionBuild
AppId={{A10F0E4B-E548-4C9A-B93F-5B05493AA844}
#else
AppId={{AADD80D2-54CD-4FD9-BB42-A669D15C8B45}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Anything Plays
#ifdef ProductionBuild
DefaultDirName={autopf}\Anything Plays
DefaultGroupName=Anything Plays
#else
DefaultDirName={autopf}\Anything Plays 3.0 Preview
DefaultGroupName=Anything Plays 3.0 Preview
#endif
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=AnythingPlaysSetup-{#AppVersion}
SetupIconFile=..\build\v21-icon\anything_plays.ico
UninstallDisplayIcon={app}\AnythingPlays.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\AnythingPlays\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
#ifdef ProductionBuild
Name: "{group}\Anything Plays"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#else
Name: "{group}\Anything Plays 3.0 Preview"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 3.0 Preview"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\AnythingPlays.exe"; Description: "Launch Anything Plays"; Flags: nowait postinstall skipifsilent
