#include "version.iss"

#ifndef NexusBuildDir
#define NexusBuildDir "..\dist\NEXUS"
#endif

[Setup]
; Double braces escape the literal GUID syntax in Inno Setup constants.
AppId={{A8F713A4-82E7-44C9-A5B7-44548D6511D0}}
AppName=NEXUS
AppVersion={#NexusVersion}
AppVerName=NEXUS {#NexusVersion}
AppPublisher=NEXUS Project
DefaultDirName={localappdata}\Programs\NEXUS
DefaultGroupName=NEXUS
DisableProgramGroupPage=yes
DisableWelcomePage=no
UsePreviousAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\release
OutputBaseFilename=NEXUS-Setup-{#NexusVersion}-x64
SetupIconFile=..\assets\nexus.ico
UninstallDisplayIcon={app}\NEXUS.exe
LicenseFile=..\LICENSE
InfoAfterFile=..\docs\THIRD_PARTY_NOTICES.md
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
Compression=lzma2
SolidCompression=yes
Uninstallable=yes
VersionInfoCompany=NEXUS Project
VersionInfoDescription=NEXUS Windows Installer
VersionInfoProductName=NEXUS
; Windows VERSIONINFO requires a numeric dotted version; AppVersion retains
; the full semantic prerelease string shown by the installer.
VersionInfoProductVersion={#NexusFileVersion}
VersionInfoVersion={#NexusFileVersion}
UninstallDisplayName=NEXUS
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#NexusBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NEXUS"; Filename: "{app}\NEXUS.exe"; IconFilename: "{app}\NEXUS.exe"
Name: "{autodesktop}\NEXUS"; Filename: "{app}\NEXUS.exe"; Tasks: desktopicon; IconFilename: "{app}\NEXUS.exe"

[Run]
Filename: "{app}\NEXUS.exe"; Description: "Launch NEXUS {#NexusVersion}"; Flags: nowait postinstall skipifsilent

[Code]
function NextVersionComponent(var Value: String): Integer;
var
  DotAt, DashAt, PlusAt, CutAt: Integer;
begin
  DotAt := Pos('.', Value);
  DashAt := Pos('-', Value);
  PlusAt := Pos('+', Value);
  CutAt := Length(Value) + 1;
  if (DotAt > 0) and (DotAt < CutAt) then CutAt := DotAt;
  if (DashAt > 0) and (DashAt < CutAt) then CutAt := DashAt;
  if (PlusAt > 0) and (PlusAt < CutAt) then CutAt := PlusAt;
  Result := StrToIntDef(Copy(Value, 1, CutAt - 1), -1);
  Delete(Value, 1, CutAt);
end;

function PrereleasePart(Value: String): String;
var
  DashAt, PlusAt, EndAt: Integer;
begin
  Result := '';
  DashAt := Pos('-', Value);
  if DashAt = 0 then Exit;
  PlusAt := Pos('+', Value);
  EndAt := Length(Value) + 1;
  if (PlusAt > DashAt) then EndAt := PlusAt;
  Result := Copy(Value, DashAt + 1, EndAt - DashAt - 1);
end;

function IsNumericIdentifier(Value: String): Boolean;
var I: Integer;
begin
  Result := (Value <> '');
  for I := 1 to Length(Value) do begin
    if Pos(Copy(Value, I, 1), '0123456789') = 0 then begin
      Result := False;
      Exit;
    end;
  end;
end;

function NextPrereleaseIdentifier(var Value: String): String;
var DotAt: Integer;
begin
  DotAt := Pos('.', Value);
  if DotAt = 0 then begin
    Result := Value;
    Value := '';
  end else begin
    Result := Copy(Value, 1, DotAt - 1);
    Delete(Value, 1, DotAt);
  end;
end;

function ComparePrereleaseIdentifiers(NewValue, ExistingValue: String): Integer;
var NewIdentifier, ExistingIdentifier: String; NewNumeric, ExistingNumeric: Boolean;
begin
  Result := 0;
  while (NewValue <> '') or (ExistingValue <> '') do begin
    if NewValue = '' then begin Result := -1; Exit; end;
    if ExistingValue = '' then begin Result := 1; Exit; end;
    NewIdentifier := NextPrereleaseIdentifier(NewValue);
    ExistingIdentifier := NextPrereleaseIdentifier(ExistingValue);
    NewNumeric := IsNumericIdentifier(NewIdentifier);
    ExistingNumeric := IsNumericIdentifier(ExistingIdentifier);
    if NewNumeric and ExistingNumeric then begin
      if Length(NewIdentifier) < Length(ExistingIdentifier) then begin Result := -1; Exit; end;
      if Length(NewIdentifier) > Length(ExistingIdentifier) then begin Result := 1; Exit; end;
      Result := CompareStr(NewIdentifier, ExistingIdentifier);
    end else if NewNumeric <> ExistingNumeric then begin
      if NewNumeric then Result := -1 else Result := 1;
    end else begin
      Result := CompareStr(NewIdentifier, ExistingIdentifier);
    end;
    if Result <> 0 then Exit;
  end;
end;

function NumericVersionOlder(NewVersion, ExistingVersion: String): Boolean;
var
  I, NewValue, OldValue: Integer;
  NewPrerelease, ExistingPrerelease: String;
begin
  Result := False;
  NewPrerelease := PrereleasePart(NewVersion);
  ExistingPrerelease := PrereleasePart(ExistingVersion);
  for I := 1 to 3 do begin
    NewValue := NextVersionComponent(NewVersion);
    OldValue := NextVersionComponent(ExistingVersion);
    if (NewValue < 0) or (OldValue < 0) then begin Result := False; Exit; end;
    if NewValue < OldValue then begin Result := True; Exit; end;
    if NewValue > OldValue then begin Result := False; Exit; end;
  end;
  if (NewPrerelease <> '') and (ExistingPrerelease = '') then Result := True
  else if (NewPrerelease = '') and (ExistingPrerelease <> '') then Result := False
  else if ComparePrereleaseIdentifiers(NewPrerelease, ExistingPrerelease) < 0 then Result := True;
end;

function InitializeSetup(): Boolean;
var ExistingVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A8F713A4-82E7-44C9-A5B7-44548D6511D0}_is1',
    'DisplayVersion', ExistingVersion) then begin
    if NumericVersionOlder('{#NexusVersion}', ExistingVersion) then begin
      MsgBox('NEXUS ' + ExistingVersion + ' is already installed. This installer cannot downgrade it to {#NexusVersion}.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

var RemoveNexusData: Boolean;

function InitializeUninstall(): Boolean;
begin
  RemoveNexusData := False;
  Result := True;
  if MsgBox('Keep your NEXUS settings, performance history, gaming history, logs, and reports? Choose No only if you also want to remove all data in %LOCALAPPDATA%\Nexus.', mbConfirmation, MB_YESNO) = IDNO then
    RemoveNexusData := True;
end;

procedure DeinitializeUninstall();
var DataPath: String;
begin
  if RemoveNexusData then begin
    DataPath := ExpandConstant('{localappdata}\Nexus');
    if CompareText(ExtractFileName(DataPath), 'Nexus') = 0 then
      DelTree(DataPath, True, True, True);
  end;
end;
