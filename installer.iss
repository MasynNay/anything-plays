#define AppName "Anything Plays 2.1 Test"
#ifndef AppVersion
  #define AppVersion "2.1.0-alpha.1"
#endif
[Setup]
AppId={{1DCC721E-A1D2-4A91-8B49-C7A453EEDB21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Anything Plays
DefaultDirName={autopf}\Anything Plays 2.1 Test
DefaultGroupName=Anything Plays 2.1 Test
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=AnythingPlaysSetup-{#AppVersion}
SetupIconFile=assets\anything_plays.ico
UninstallDisplayIcon={app}\AnythingPlays.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\AnythingPlays\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Anything Plays 2.1 Test"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays 2.1 Test"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\AnythingPlays.exe"; Description: "Launch Anything Plays"; Flags: nowait postinstall skipifsilent
