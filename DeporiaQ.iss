#define MyAppName "DeporiaQ"
#define MyAppVersion "0.23.0"
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
CloseApplications=force
RestartApplications=no
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

Source: "deporiaq_restart.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C schtasks /Delete /F /TN ""DeporiaQ Update Check"" >nul 2>&1"; Flags: runhidden waituntilterminated
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\deporiaq_restart.ps1"" -AppPath ""{app}\{#MyAppExeName}"" -Version ""{#MyAppVersion}"" -SetupProcessId {code:SetupPID}"; Description: "DeporiaQ'yu başlat"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent runasoriginaluser runhidden
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\deporiaq_restart.ps1"" -AppPath ""{app}\{#MyAppExeName}"" -Version ""{#MyAppVersion}"" -SetupProcessId {code:SetupPID}"; WorkingDir: "{app}"; Flags: nowait skipifnotsilent runasoriginaluser runhidden

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""DeporiaQ Update Check"""; Flags: runhidden waituntilterminated; RunOnceId: "DeporiaQUpdateTaskDelete"

[Code]
function GetCurrentProcessId: LongWord;
  external 'GetCurrentProcessId@kernel32.dll stdcall';

function SetupPID(Param: String): String;
begin
  Result := IntToStr(GetCurrentProcessId);
end;
