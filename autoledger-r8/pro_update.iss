[Setup]
; R8 UPDATE package: same AppId/AppData as R6. Existing ALP225R6 entitlement is preserved.
AppId=AUTOLEDGER-Pro-v2.2.5-R6
AppName=AUTOLEDGER Pro
AppVersion=2.2.5 R8 TEST
AppPublisher=AUTOLEDGER SYSTEMS PTY LTD
AppPublisherURL=https://autoledger.co.za
DefaultDirName={localappdata}\Programs\AUTOLEDGER Pro
DefaultGroupName=AUTOLEDGER
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=AUTOLEDGER_Pro_v2.2.5_R8_UPDATE_from_R6_TEST_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=EULA.txt
SetupIconFile=assets\AUTOLEDGER_ICON.ico
UninstallDisplayIcon={app}\AUTOLEDGER Pro v2.2.5 R8 TEST.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[InstallDelete]
Type: files; Name: "{app}\AUTOLEDGER Pro v2.2.5 R6 TEST.exe"

[Files]
Source: "package\pro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AUTOLEDGER Pro"; Filename: "{app}\AUTOLEDGER Pro v2.2.5 R8 TEST.exe"
Name: "{autodesktop}\AUTOLEDGER Pro"; Filename: "{app}\AUTOLEDGER Pro v2.2.5 R8 TEST.exe"

[Code]
var
  RemoveLocalData: Boolean;

function ExistingInstallFound(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Pro\AUTOLEDGER Pro v2.2.5 R6 TEST.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Pro\AUTOLEDGER Pro v2.2.5 R8 TEST.exe'));
end;

function InitializeSetup(): Boolean;
begin
  Result := ExistingInstallFound();
  if not Result then
    MsgBox('This is the AUTOLEDGER Pro R8 UPDATE package, but an existing R6/R8 Pro installation was not found.' + #13#10 + #13#10 +
      'Please use the R8 FULL installer on a new PC or clean installation.', mbError, MB_OK);
end;

function InitializeUninstall(): Boolean;
begin
  RemoveLocalData := MsgBox(
    'Also remove AUTOLEDGER local data and settings?' + #13#10 + #13#10 +
    'Select Yes to permanently remove AUTOLEDGER Pro profiles, settings, entitlement and device-activation data.' + #13#10 +
    'Select No to preserve them for a future reinstall/update.',
    mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveLocalData then
    DelTree(ExpandConstant('{userappdata}\AUTOLEDGER_V225_TEST_Pro'), True, True, True);
end;
