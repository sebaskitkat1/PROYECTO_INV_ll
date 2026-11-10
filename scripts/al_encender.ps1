# Al encender el equipo: cajero diario sin ventanas modales.
# Se registra con scripts/registrar_al_encender.ps1 (tarea al iniciar sesion).

$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$log = Join-Path $project "scripts\cajero_diario.log"

function Write-Log([string]$texto) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $log -Value "[$timestamp] $texto"
}

Write-Log "Al encender: iniciando cajero diario."

# 1) Intentar levantar MySQL si esta detenido.
$svc = Get-Service -Name "MySQL80" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne "Running") {
    Write-Log "MySQL80 detenido; intentando iniciar."
    try {
        Start-Service -Name "MySQL80" -ErrorAction Stop
    } catch {
        Write-Log "No se pudo iniciar MySQL80: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 6
}

# 2) Esperar a que la base este disponible (hasta ~1 minuto).
$ok = $false
for ($i = 0; $i -lt 12; $i++) {
    $res = python -c "import sys; sys.path.insert(0, r'$project'); from app.data import db; print('OK' if db.available() else 'NO')" 2>$null
    if ($res -eq "OK") { $ok = $true; break }
    Start-Sleep -Seconds 5
}

if (-not $ok) {
    Write-Log "No se pudo conectar a MySQL. Ejecuta manualmente: python scripts\cajero_diario.py"
    exit 1
}

# 3) Ejecutar el cajero diario. El script evita duplicar el dia.
Write-Log "Ejecutando cajero diario."
python "$project\scripts\cajero_diario.py" --tickets 30 2>&1 | Out-File -Append -FilePath $log
Write-Log "Cajero diario terminado."
