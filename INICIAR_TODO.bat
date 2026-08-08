@echo off
title TalkIA PRO - Iniciando Todo
color 0E
echo ========================================================
echo    Iniciando TalkIA PRO (Bot + Servidor Web)
echo ========================================================
echo.
cd /d "%~dp0"
start "Bot Traductor" cmd /k "python bot_traductor.py"
start "Servidor Web Hotel" cmd /k "python servidor_talia.py"
echo Todo iniciado correctamente.
