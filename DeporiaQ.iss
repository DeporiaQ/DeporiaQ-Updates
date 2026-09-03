#define MyAppName "DeporiaQ"
#define MyAppVersion "0.18.0"
#define MyAppPublisher "DeporiaQ"
#define MyAppExeName "DeporiaQ.exe"

[Setup]
AppId={{A92C0C5B-8B8D-43D5-9139-7B9917BD6C30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=kurulum
OutputBaseFilename=DeporiaQ_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupLogging=yes
SetupIconFile=deporiaq_icon.ico

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek görevler:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\DeporiaQUpdate.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "guncelleme_ayarlari.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "BILDIRICI_GOREV_KUR.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\BILDIRICI_GOREV_KUR.bat"; Flags: runhidden waituntilterminated
Filename: "{app}\DeporiaQUpdate.exe"; Flags: nowait runhidden skipifsilent
Filename: "{app}\{#MyAppExeName}"; Description: "DeporiaQ'yu başlat"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""DeporiaQ Update Check"""; Flags: runhidden waituntilterminated; RunOnceId: "DeporiaQUpdateTaskDelete"
