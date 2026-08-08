@echo off
title TalkIA PRO - Plataforma Web del Hotel
color 0B
echo ========================================================
echo    Iniciando Servidor Web del Hotel (Dashboards)
echo ========================================================
echo.
cd /d "%~dp0"
python servidor_talia.py
pause
