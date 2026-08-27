[Setup]
AppId=AUTOLEDGER-Free-v2.2.5-R6
AppName=AUTOLEDGER Free
AppVersion=2.2.5 R6 TEST
AppPublisher=AUTOLEDGER SYSTEMS PTY LTD
AppPublisherURL=https://autoledger.co.za
DefaultDirName={localappdata}\Programs\AUTOLEDGER Free
DefaultGroupName=AUTOLEDGER
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=AUTOLEDGER_Free_v2.2.5_R6_STANDALONE_TEST_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=EULA.txt
UninstallDisplayIcon={app}\AUTOLEDGER Free v2.2.5 R6 TEST.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "package\free\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AUTOLEDGER Free"; Filename: "{app}\AUTOLEDGER Free v2.2.5 R6 TEST.exe"
Name: "{autodesktop}\AUTOLEDGER Free"; Filename: "{app}\AUTOLEDGER Free v2.2.5 R6 TEST.exe"; Tasks: desktopicon

[Code]
var
  RemoveLocalData: Boolean;

function InitializeUninstall(): Boolean;
begin
  RemoveLocalData := MsgBox(
    'Also remove AUTOLEDGER local data and settings?' + #13#10 + #13#10 +
    'Select Yes to permanently remove AUTOLEDGER Free profiles, settings and usage data.' + #13#10 +
    'Select No to preserve them for a future reinstall.',
    mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveLocalData then
    DelTree(ExpandConstant('{userappdata}\AUTOLEDGER_V225_TEST_Free'), True, True, True);
end;
