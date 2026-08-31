; Instalador Windows do WebRP Extrator (Inno Setup 6)
#define MyAppName "WebRP Extrator"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Web Rio Preto"
#define MyAppURL "https://extrator.webriopreto.com"
#define MyAppExeName "WebRP-Extrator.exe"

[Setup]
AppId={{A8E4C2B1-7D3F-4E91-9B2A-WebRPExtrator01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\WebRP Extrator
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..
OutputBaseFilename=WebRP-Extrator-Setup
SetupIconFile=..\build\webrp-extrator.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "..\dist\WebRP-Extrator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  BatPath: string;
begin
  if CurStep = ssPostInstall then
  begin
    { Garante PLAYWRIGHT_BROWSERS_PATH via atalho WorkingDir + env no exe }
    BatPath := ExpandConstant('{app}\WebRP-Extrator.bat');
    if FileExists(BatPath) then
      DeleteFile(BatPath);
  end;
end;
