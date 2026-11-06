#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef AppSource
  #error AppSource is required
#endif
#ifndef OutputDir
  #error OutputDir is required
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
LanguageDetectionMethod=none
UsePreviousLanguage=no
ShowLanguageDialog=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
chinesesimplified.UninstallShortcut=卸载 %1
english.UninstallShortcut=Uninstall %1
chinesesimplified.LaunchApp=运行 %1
english.LaunchApp=Launch %1

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Easy Cidaren"; Filename: "{app}\EasyCidaren.exe"
Name: "{group}\{cm:UninstallShortcut,Easy Cidaren}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\EasyCidaren.exe"; Description: "{cm:LaunchApp,Easy Cidaren}"; Flags: nowait postinstall skipifsilent
