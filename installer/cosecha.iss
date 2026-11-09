#ifndef AppVersion
#define AppVersion "1.0.0"
#endif

[Setup]
AppId={{5D71870A-B0AB-4AB7-9BB0-E3EE09B6114C}
AppName=Cosecha
AppVersion={#AppVersion}
AppVerName=Cosecha {#AppVersion}
AppPublisher=CafeData
DefaultDirName={localappdata}\Programs\Cosecha
DefaultGroupName=Cosecha
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=Cosecha-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\cosecha.exe
SetupLogging=yes
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\dist\cosecha\*"; DestDir: "{app}"; Excludes: ".env,.env.*,*.pyc,__pycache__,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion
Source: "..\db\frutidata_schema.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_ordenes_pendientes.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_catalogo_pos.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_fix_totales_ventas.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_cantidades_decimales.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_inventario_recetas.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\migrate_kpi_precio_unidad.sql"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\db\README_datos.md"; DestDir: "{app}\db"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_INSTALACION.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Cosecha"; Filename: "{app}\cosecha.exe"; WorkingDir: "{app}"
Name: "{group}\Configurar base de datos"; Filename: "notepad.exe"; Parameters: """{app}\.env"""; WorkingDir: "{app}"
Name: "{group}\Leer instalacion"; Filename: "{app}\LEEME_INSTALACION.txt"
Name: "{autodesktop}\Cosecha"; Filename: "{app}\cosecha.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "notepad.exe"; Parameters: """{app}\.env"""; Description: "Configurar base de datos (editar .env)"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\cosecha.exe"; Description: "Abrir Cosecha"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\.env"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Origen, Destino: String;
begin
  if CurStep = ssPostInstall then
  begin
    Origen := ExpandConstant('{app}\.env.example');
    Destino := ExpandConstant('{app}\.env');
    if FileExists(Origen) and not FileExists(Destino) then
      FileCopy(Origen, Destino, False);
  end;
end;
