# Registra el cajero diario a las 08:00.
# SOLO PARA ENTORNOS DEMO: el cajero exige COSECHA_ENTORNO=demo y nunca debe
# apuntar a una base con ventas reales.
$bat = Join-Path $PSScriptRoot "run_cajero_diario.bat"
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$bat`""
$trigger = New-ScheduledTaskTrigger -Daily -At '08:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'CosechaCajeroDiario' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName 'CosechaCajeroDiario' | Select-Object TaskName, State