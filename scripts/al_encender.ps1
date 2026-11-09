# Al encender el equipo: recordatorio + cajero diario
# Se registra con scripts/registrar_al_encender.ps1 (tarea al iniciar sesion).

$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

Add-Type -AssemblyName System.Windows.Forms

# 1) Recordatorio inicial
[System.Windows.Forms.MessageBox]::Show("Al encender: abre MySQL (servicio MySQL80) para que el cajero diario se ejecute.", "Cosecha - Recordatorio", "OK", "Information") | Out-Null

# 2) Intentar levantar MySQL si esta detenido
$svc = Get-Service -Name "MySQL80" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne "Running") {
    [System.Windows.Forms.MessageBox]::Show("MySQL esta detenido. Intentando iniciarlo...", "Cosecha", "OK", "Warning") | Out-Null
    try { Start-Service -Name "MySQL80" -ErrorAction Stop } catch { }
    Start-Sleep -Seconds 6
}

# 3) Esperar a que la base este disponible (hasta ~1 minuto)
$ok = $false
for ($i = 0; $i -lt 12; $i++) {
    $res = python -c "import sys; sys.path.insert(0, r'$project'); from app.data import db; print('OK' if db.available() else 'NO')" 2>$null
    if ($res -eq "OK") { $ok = $true; break }
    Start-Sleep -Seconds 5
}

if (-not $ok) {
    [System.Windows.Forms.MessageBox]::Show("No se pudo conectar a MySQL. Abre MySQL y ejecuta manualmente: python scripts\cajero_diario.py", "Cosecha", "OK", "Error") | Out-Null
    exit 1
}

# 4) Ejecutar el cajero diario
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "$project\scripts\cajero_diario.log" -Value "`n===== $timestamp (al encender) ====="
python "$project\scripts\cajero_diario.py" --tickets 30 2>&1 | Out-File -Append -FilePath "$project\scripts\cajero_diario.log"

[System.Windows.Forms.MessageBox]::Show("Cajero diario de Cosecha ejecutado. Revisa scripts\cajero_diario.log", "Cosecha", "OK", "Information") | Out-Null