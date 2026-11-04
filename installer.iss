#define AppName "Anything Plays"
#ifndef AppVersion
  #define AppVersion "1.5.0"
#endif
[Setup]
AppId={{D5C81347-28B4-4F0D-BA82-1D441A83C0F5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Anything Plays
DefaultDirName={autopf}\Anything Plays
DefaultGroupName=Anything Plays
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
Name: "{group}\Anything Plays"; Filename: "{app}\AnythingPlays.exe"
Name: "{autodesktop}\Anything Plays"; Filename: "{app}\AnythingPlays.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\AnythingPlays.exe"; Description: "Launch Anything Plays"; Flags: nowait postinstall skipifsilent
