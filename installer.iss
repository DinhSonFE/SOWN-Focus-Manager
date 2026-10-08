#define AppName "SOWN Focus Manager"
#define AppVersion "4.6.0"
[Setup]
AppId={{C8B5BEB9-6759-4808-91FA-A95DCC2C7B90}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=SOWN LIGHTING
SetupIconFile=assets\app.ico
DefaultDirName={autopf}\\SOWN Focus Manager
DefaultGroupName=SOWN LIGHTING
OutputDir=installer_output
OutputBaseFilename=SOWN_Focus_Manager_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\\SOWN_Focus_Manager.exe
[Files]
Source: "dist\\SOWN_Focus_Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\\SOWN Focus Manager"; Filename: "{app}\\SOWN_Focus_Manager.exe"
Name: "{autodesktop}\\SOWN Focus Manager"; Filename: "{app}\\SOWN_Focus_Manager.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\\SOWN_Focus_Manager.exe"; Description: "Launch SOWN Focus Manager"; Flags: nowait postinstall skipifsilent
