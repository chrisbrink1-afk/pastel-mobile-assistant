[Setup]
AppId=AUTOLEDGER-Free-v2.2.5-R6
AppName=AUTOLEDGER Free
AppVersion=2.2.5 R10 TEST
AppPublisher=AUTOLEDGER SYSTEMS PTY LTD
AppPublisherURL=https://autoledgersystems.co.za
DefaultDirName={localappdata}\Programs\AUTOLEDGER Free
DefaultGroupName=AUTOLEDGER
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=AUTOLEDGER_Free_v2.2.5_R10_FULL_STANDALONE_TEST_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=EULA.txt
SetupIconFile=assets\AUTOLEDGER_ICON.ico
UninstallDisplayIcon={app}\AUTOLEDGER Free v2.2.5 R10 TEST.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[InstallDelete]
Type: files; Name: "{app}\AUTOLEDGER Free v2.2.5 R6 TEST.exe"
Type: files; Name: "{app}\AUTOLEDGER Free v2.2.5 R8 TEST.exe"
Type: files; Name: "{app}\AUTOLEDGER Free v2.2.5 R9 TEST.exe"

[Files]
Source: "package\free\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "EULA.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AUTOLEDGER Free"; Filename: "{app}\AUTOLEDGER Free v2.2.5 R10 TEST.exe"
Name: "{autodesktop}\AUTOLEDGER Free"; Filename: "{app}\AUTOLEDGER Free v2.2.5 R10 TEST.exe"

[Code]
var
  RemoveLocalData: Boolean;
  WasExistingInstall: Boolean;

function ExistingInstallFound(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Free\AUTOLEDGER Free v2.2.5 R6 TEST.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Free\AUTOLEDGER Free v2.2.5 R8 TEST.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Free\AUTOLEDGER Free v2.2.5 R9 TEST.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\AUTOLEDGER Free\AUTOLEDGER Free v2.2.5 R10 TEST.exe'));
end;

function InitializeSetup(): Boolean;
begin
  WasExistingInstall := ExistingInstallFound();
  Result := True;
end;

procedure WriteTutorialInstallContext();
var
  DataDir, Kind: String;
begin
  DataDir := ExpandConstant('{userappdata}\AUTOLEDGER_V225_TEST_Free');
  ForceDirectories(DataDir);
  if WasExistingInstall then Kind := 'update' else Kind := 'clean';
  SaveStringToFile(AddBackslash(DataDir) + 'install_context_r10.json',
    '{"revision":"R10","install_kind":"' + Kind + '"}', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteTutorialInstallContext();
end;

function InitializeUninstall(): Boolean;
begin
  RemoveLocalData := MsgBox(
    'Also remove AUTOLEDGER local data and settings?' + #13#10 + #13#10 +
    'Select Yes to permanently remove AUTOLEDGER Free profiles, settings and usage data.' + #13#10 +
    'Select No to preserve them for a future reinstall/update.',
    mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveLocalData then
    DelTree(ExpandConstant('{userappdata}\AUTOLEDGER_V225_TEST_Free'), True, True, True);
end;
