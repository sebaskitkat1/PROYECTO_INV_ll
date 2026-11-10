# Registra la tarea para ejecutar al iniciar sesion (al encender el equipo).
# El Startup de Windows tambien puede lanzar el .bat; el candado de
# al_encender.ps1 evita que ambos corran el cajero a la vez.
$taskName = "CosechaCajeroAlEncender"
$scriptPath = Join-Path $PSScriptRoot "al_encender.ps1"
$usuario = "$env:USERDOMAIN\$env:USERNAME"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$trigger.Delay = "PT15S"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Cajero diario de Cosecha al iniciar sesion" `
    -Force | Out-Null

Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
