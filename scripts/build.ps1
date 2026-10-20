$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python -m PyInstaller --noconfirm --clean --distpath "$root\dist" --workpath "$root\build" "$root\cosecha.spec"
Write-Host "Listo: $root\dist\cosecha\cosecha.exe"
