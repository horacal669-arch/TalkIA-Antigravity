@echo off
title TalkIA Antigravity - Plataforma Web del Hotel
color 0B
echo ========================================================
echo    Iniciando Servidor Web del Hotel (Dashboards)
echo ========================================================
echo.
cd /d "%~dp0"
if exist "C:\Users\horac\Documents\python_standalone\python.exe" (
    "C:\Users\horac\Documents\python_standalone\python.exe" servidor_talia.py
) else (
    python servidor_talia.py
)
pause
