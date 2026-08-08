@echo off
title TalkIA Antigravity - Iniciando Todo
color 0E
echo ========================================================
echo    Iniciando TalkIA Antigravity (Bot + Servidor Web)
echo ========================================================
echo.
cd /d "%~dp0"
if exist "C:\Users\horac\Documents\python_standalone\python.exe" (
    start "Bot Traductor" cmd /k ""C:\Users\horac\Documents\python_standalone\python.exe" bot_traductor.py"
    start "Servidor Web Hotel" cmd /k ""C:\Users\horac\Documents\python_standalone\python.exe" servidor_talia.py"
) else (
    start "Bot Traductor" cmd /k "python bot_traductor.py"
    start "Servidor Web Hotel" cmd /k "python servidor_talia.py"
)
echo Todo iniciado correctamente.
