; Compile after build_offline_windows.ps1; never distribute the source checkout.
#ifndef AppVersion
  #error AppVersion must be supplied by the build script
#endif
#ifndef FileVersion
  #error FileVersion must be supplied by the build script
#endif
#ifndef BundleDir
  #error BundleDir must be supplied by the build script
#endif
#ifndef OutputDir
  #error OutputDir must be supplied by the build script
#endif

[Setup]
AppId={{4967F753-5541-4B50-9726-BA7B9AAC122B}
AppName=NJIT Thesis Auditor
AppVersion={#AppVersion}
VersionInfoVersion={#FileVersion}
AppPublisher=Soroush Vahidi
DefaultDirName={localappdata}\Programs\NJIT Thesis Auditor
DefaultGroupName=NJIT Thesis Auditor
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.22000
OutputDir={#OutputDir}
OutputBaseFilename=NJIT-Thesis-Auditor-Setup-{#AppVersion}
SetupIconFile=..\assets\icons\njit-auditor.ico
UninstallDisplayIcon={app}\NJIT Thesis Auditor.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
Uninstallable=yes

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\NJIT Thesis Auditor"; Filename: "{app}\NJIT Thesis Auditor.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\NJIT Thesis Auditor"; Filename: "{app}\NJIT Thesis Auditor.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\NJIT Thesis Auditor.exe"; Description: "Launch NJIT Thesis Auditor"; Flags: nowait postinstall skipifsilent

; The standard uninstaller removes installed files and shortcuts. It deliberately
; never recursively deletes user-selected directories, PDFs, or exported reports.
