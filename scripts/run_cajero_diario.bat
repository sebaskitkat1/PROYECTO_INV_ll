@echo off
rem Lanzador del cajero diario. Delega en al_encender.ps1 para reutilizar el
rem candado, la espera de MySQL y el registro en scripts\cajero_diario.log.
rem No redirijas la salida a ese log: Python lo abre y Windows no permite dos
rem escritores a la vez (PermissionError).
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0al_encender.ps1"
exit /b %ERRORLEVEL%
