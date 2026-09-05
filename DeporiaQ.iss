#define MyAppName "DeporiaQ"
#define MyAppVersion "0.21.2"
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

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C schtasks /Delete /F /TN ""DeporiaQ Update Check"" >nul 2>&1"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "DeporiaQ'yu başlat"; Flags: nowait postinstall

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""DeporiaQ Update Check"""; Flags: runhidden waituntilterminated; RunOnceId: "DeporiaQUpdateTaskDelete"

[Code]
function ParametreVar(Aranan: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Aranan) = 0 then begin Result := True; Exit; end;
end;

function InitializeSetup(): Boolean;
var
  Kod: Integer;
begin
  Result := True;
  { 0.20 ve daha eski güncelleyiciler parametre vermese bile kurulumu sessiz sürdür. }
  if (not WizardSilent) and (not ParametreVar('/DEPORIAQ_SILENT')) then
  begin
    ShellExec('', ExpandConstant('{srcexe}'), '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS /DEPORIAQ_SILENT', '', SW_SHOW, ewNoWait, Kod);
    Result := False;
  end;
end;
