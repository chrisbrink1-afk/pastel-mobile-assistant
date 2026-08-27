[Setup]
AppId=AUTOLEDGER-Pro-v2.2.5-R6
AppName=AUTOLEDGER Pro
AppVersion=2.2.5 R6 TEST
AppPublisher=AUTOLEDGER SYSTEMS PTY LTD
AppPublisherURL=https://autoledger.co.za
DefaultDirName={localappdata}\Programs\AUTOLEDGER Pro
DefaultGroupName=AUTOLEDGER
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=AUTOLEDGER_Pro_v2.2.5_R6_STANDALONE_TEST_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=EULA.txt
UninstallDisplayIcon={app}\AUTOLEDGER Pro v2.2.5 R6 TEST.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "package\pro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AUTOLEDGER Pro"; Filename: "{app}\AUTOLEDGER Pro v2.2.5 R6 TEST.exe"
Name: "{autodesktop}\AUTOLEDGER Pro"; Filename: "{app}\AUTOLEDGER Pro v2.2.5 R6 TEST.exe"; Tasks: desktopicon

[Code]
var
  RemoveLocalData: Boolean;

function InitializeUninstall(): Boolean;
begin
  RemoveLocalData := MsgBox(
    'Also remove AUTOLEDGER local data and settings?' + #13#10 + #13#10 +
    'Select Yes to permanently remove AUTOLEDGER Pro profiles, settings and locally stored licence data.' + #13#10 +
    'Select No to preserve them for a future reinstall.',
    mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveLocalData then
    DelTree(ExpandConstant('{userappdata}\AUTOLEDGER_V225_TEST_Pro'), True, True, True);
end;
