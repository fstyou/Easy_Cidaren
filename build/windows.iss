#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef AppSource
  #error AppSource is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef AppArch
  #error AppArch is required
#endif
#ifndef InnoArch
  #error InnoArch is required
#endif
#ifndef OutputName
  #error OutputName is required
#endif

[Setup]
AppId={{E550EB68-1ED8-49E6-AE03-8103ED5AA7CE}
AppName=Easy Cidaren
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\EasyCidaren
DefaultGroupName=Easy Cidaren
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
ArchitecturesAllowed={#InnoArch}
ArchitecturesInstallIn64BitMode={#InnoArch}
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\EasyCidaren.exe

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Easy Cidaren"; Filename: "{app}\EasyCidaren.exe"
Name: "{group}\卸载 Easy Cidaren"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\EasyCidaren.exe"; Description: "运行 Easy Cidaren"; Flags: nowait postinstall skipifsilent
