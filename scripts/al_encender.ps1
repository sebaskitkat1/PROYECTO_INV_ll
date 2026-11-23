# Al encender el equipo: cajero diario sin ventanas modales.
# Se registra con scripts/registrar_al_encender.ps1 o con el acceso del
# Startup de Windows. Un candado evita dos corridas simultaneas.

$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$log = Join-Path $project "scripts\cajero_diario.log"
$estadoDir = Join-Path $env:LOCALAPPDATA "Cosecha"
$estado = Join-Path $estadoDir "cajero_ultimo_estado.txt"
$lock = Join-Path $estadoDir "cajero.lock"

New-Item -ItemType Directory -Path $estadoDir -Force | Out-Null

function Write-Log([string]$texto) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $log -Value "[$timestamp] $texto" -Encoding utf8
}

function Write-Estado([string]$texto) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Set-Content -Path $estado -Value "[$timestamp] $texto" -Encoding utf8
}

# Candado atomico con deteccion de restos: un cierre forzado no debe
# bloquear el cajero para siempre.
function Test-LockActivo([string]$ruta) {
    if (-not (Test-Path -LiteralPath $ruta)) { return $false }
    $item = Get-Item -LiteralPath $ruta -ErrorAction SilentlyContinue
    if (-not $item) { return $false }
    if (((Get-Date) - $item.LastWriteTime).TotalHours -ge 2) { return $false }
    $primera = Get-Content -LiteralPath $ruta -ErrorAction SilentlyContinue |
        Select-Object -First 1
    $pidLock = 0
    if ($primera -and [int]::TryParse(
            ([string]$primera).Trim().Split(" ")[0], [ref]$pidLock)) {
        return [bool](Get-Process -Id $pidLock -ErrorAction SilentlyContinue)
    }
    return $true
}

$lockStream = $null
for ($intento = 1; $intento -le 2; $intento++) {
    try {
        $lockStream = [System.IO.File]::Open(
            $lock, [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        break
    } catch {
        if ($intento -eq 1 -and -not (Test-LockActivo $lock)) {
            Write-Log "Candado viejo detectado; se elimina y se reintenta."
            Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
            continue
        }
        Write-Log "Ya hay otra corrida del cajero en curso; se omite esta."
        exit 0
    }
}
if (-not $lockStream) {
    Write-Log "No se pudo crear el candado; se omite esta corrida."
    exit 0
}
$datosLock = [System.Text.Encoding]::UTF8.GetBytes("$PID`n")
$lockStream.Write($datosLock, 0, $datosLock.Length)
$lockStream.Flush()

try {
    $inicio = Get-Date
    $arranque = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
    Write-Log "Al encender: iniciando cajero diario (arranque: $($arranque.ToString('yyyy-MM-dd HH:mm:ss')))."
    Write-Estado "iniciando"

    # 1) Python disponible en este usuario.
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        Write-Log "No se encontro python en PATH. Revisa la instalacion de Python."
        Write-Estado "error: python no encontrado"
        exit 1
    }

    # 2) Intentar levantar MySQL si esta detenido.
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

    # 3) Esperar a que la base este disponible (hasta ~2 minutos).
    $ok = $false
    for ($i = 1; $i -le 24; $i++) {
        $res = & $python -c "import sys; sys.path.insert(0, r'$project'); from app.data import db; print('OK' if db.available() else 'NO')" 2>$null
        if (($res | Select-Object -Last 1) -eq "OK") {
            $ok = $true
            break
        }
        if ($i -eq 1 -or ($i % 6) -eq 0) {
            Write-Log "Esperando MySQL ($i/24)..."
        }
        Start-Sleep -Seconds 5
    }

    if (-not $ok) {
        Write-Log "No se pudo conectar a MySQL. Ejecuta manualmente: python scripts\cajero_diario.py"
        Write-Estado "error: sin conexion a MySQL"
        exit 1
    }

    # 4) Ejecutar el cajero. El script evita duplicar el dia.
    Write-Log "Ejecutando cajero diario."
    $salida = & $python "$project\scripts\cajero_diario.py" --tickets 30 2>&1
    $codigo = $LASTEXITCODE
    foreach ($linea in $salida) {
        Add-Content -Path $log -Value $linea -Encoding utf8
    }

    $duracion = [int]((Get-Date) - $inicio).TotalSeconds
    if ($codigo -eq 0) {
        Write-Log "Cajero diario terminado (codigo 0, $duracion s)."
        Write-Estado "ok (codigo 0, $duracion s)"
    } else {
        Write-Log "Cajero diario termino con error (codigo $codigo, $duracion s)."
        Write-Estado "error (codigo $codigo, $duracion s)"
    }
    exit $codigo
}
finally {
    if ($lockStream) {
        $lockStream.Close()
    }
    $contenido = Get-Content -LiteralPath $lock -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($contenido -and ([string]$contenido).Trim() -eq "$PID") {
        Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
    }
}
