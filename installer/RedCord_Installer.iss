#pragma codepage: 65001

#define MyAppName "RedCord Writer Desktop"
#define MyAppVersion "0.8.3"
#define MyAppPublisher "RedCord Project"
#define MyAppExeName "RedCord.exe"

[Setup]
AppId={{2A9E99CF-8E11-4D42-9B5B-0E0C0D070000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
VersionInfoVersion=0.8.3.0
DefaultDirName={autopf}\RedCord
DefaultGroupName=RedCord
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=RedCord_Setup_0_8_3
SetupIconFile=..\redcord\assets\redcord_icon.ico
WizardImageFile=assets\installer_sidebar.bmp
WizardSmallImageFile=assets\installer_wizard.bmp
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableWelcomePage=no
CloseApplications=force
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
russian.WelcomeLabel1=Добро пожаловать в установщик RedCord Writer Desktop 0.8.3
russian.WelcomeLabel2=RedCord 0.8.3 улучшает Word-like ribbon, BoC Lite, concept art и обложки.
english.WelcomeLabel1=Welcome to RedCord Writer Desktop 0.8.3 Setup
english.WelcomeLabel2=RedCord 0.8.3 improves the Word-like ribbon, BoC Lite, concept art and covers.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\redcord_build\redcord\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Dirs]
Name: "{app}\data"
Name: "{app}\commits"
Name: "{app}\data\art_assets"
Name: "{app}\data\backups"
Name: "{app}\data\update_backups"
Name: "{app}\data\pending_update"

[Icons]
Name: "{group}\RedCord"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,RedCord}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\RedCord"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,RedCord}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; User data intentionally not deleted: data/, commits/ and local settings stay in place.
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
procedure InitializeWizard();
begin
  WizardForm.Color := $080608;
  WizardForm.WelcomeLabel1.Font.Color := $F3ECF0;
  WizardForm.WelcomeLabel2.Font.Color := $B9A9AD;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
