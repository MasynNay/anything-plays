#ifdef V31FinalBuild
  #define AppName "Anything Plays 3.1"
#elif defined(V31RC2Build)
  #define AppName "Anything Plays 3.1 Release Candidate 2"
#elif defined(V31RCBuild)
  #define AppName "Anything Plays 3.1 Release Candidate 1"
#elif defined(V31PreviewBuild)
  #define AppName "Anything Plays 3.1 Preview 1"
#elif defined(ProductionBuild)
  #define AppName "Anything Plays"
#else
  #define AppName "Anything Plays 3.0 Preview"
#endif
#ifndef AppVersion
  #define AppVersion "3.0.0-alpha.1"
#endif
[Setup]
#ifdef V31FinalBuild
AppId={{753B9C90-2D6A-43E4-90E4-49393B3AE025}
#elif defined(V31RC2Build)
AppId={{779FBB2F-1ACC-456E-A088-75D395CE98A3}
#elif defined(V31RCBuild)
AppId={{A3C2BEE4-4F7E-476F-A514-940FB1E1E071}
#elif defined(V31PreviewBuild)
AppId={{C9B0B32A-78D9-47DA-B991-41AC320D10F1}
#elif defined(ProductionBuild)
AppId={{A10F0E4B-E548-4C9A-B93F-5B05493AA844}
#else
AppId={{AADD80D2-54CD-4FD9-BB42-A669D15C8B45}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Anything Plays
#ifdef V31FinalBuild
DefaultDirName={autopf}\Anything Plays 3.1
DefaultGroupName=Anything Plays 3.1
#elif defined(V31RC2Build)
DefaultDirName={autopf}\Anything Plays 3.1 Release Candidate 2
DefaultGroupName=Anything Plays 3.1 Release Candidate 2
#elif defined(V31RCBuild)
DefaultDirName={autopf}\Anything Plays 3.1 Release Candidate 1
DefaultGroupName=Anything Plays 3.1 Release Candidate 1
#elif defined(V31PreviewBuild)
DefaultDirName={autopf}\Anything Plays 3.1 Preview 1
DefaultGroupName=Anything Plays 3.1 Preview 1
#elif defined(ProductionBuild)
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
#ifdef V31FinalBuild
Name: "{group}\Anything Plays 3.1"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 3.1"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#elif defined(V31RC2Build)
Name: "{group}\Anything Plays 3.1 Release Candidate 2"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 3.1 Release Candidate 2"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#elif defined(V31RCBuild)
Name: "{group}\Anything Plays 3.1 Release Candidate 1"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 3.1 Release Candidate 1"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#elif defined(V31PreviewBuild)
Name: "{group}\Anything Plays 3.1 Preview 1"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 3.1 Preview 1"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon
#elif defined(ProductionBuild)
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
