# Registra la tarea para ejecutar al iniciar sesion (al encender el equipo).
$taskName = "CosechaCajeroAlEncender"
$scriptPath = Join-Path $PSScriptRoot "al_encender.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State