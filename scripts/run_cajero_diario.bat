@echo off
cd /d "%~dp0.."
python scripts\cajero_diario.py --tickets 30 >> scripts\cajero_diario.log 2>&1