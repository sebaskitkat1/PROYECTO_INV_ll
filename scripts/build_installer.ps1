param(
    [string]$Version = "1.0.0",
    [string]$Iscc = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root "dist\cosecha\cosecha.exe"

if (-not (Test-Path -LiteralPath $exe)) {
    throw "Falta $exe. Ejecuta primero scripts\build.ps1"
}

if (-not $Iscc) {
    if ($env:ISCC_PATH) {
        $Iscc = $env:ISCC_PATH
    } else {
        $candidatos = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
        )
        $programFilesX86 = ${env:ProgramFiles(x86)}
        if ($programFilesX86) {
            $candidatos += Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"
        }
        $Iscc = $candidatos | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
}

if (-not $Iscc -or -not (Test-Path -LiteralPath $Iscc)) {
    throw "No encontre ISCC.exe. Instala Inno Setup 6 con: winget install --id JRSoftware.InnoSetup -e"
}

$salida = Join-Path $root "dist\installer"
New-Item -ItemType Directory -Path $salida -Force | Out-Null

& $Iscc "/DAppVersion=$Version" (Join-Path $root "installer\cosecha.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup termino con codigo $LASTEXITCODE"
}

Write-Host "Listo: $salida\Cosecha-Setup-$Version.exe"
