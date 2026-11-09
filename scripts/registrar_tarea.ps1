$bat = Join-Path $PSScriptRoot "run_cajero_diario.bat"
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$bat`""
$trigger = New-ScheduledTaskTrigger -Daily -At '08:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'CosechaCajeroDiario' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName 'CosechaCajeroDiario' | Select-Object TaskName, State