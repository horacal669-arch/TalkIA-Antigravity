@echo off
title TalkIA Antigravity - Bot Traductor Personal
color 0A
echo ========================================================
echo    Iniciando Bot Traductor Personal (Telegram)
echo ========================================================
echo.
cd /d "%~dp0"
if exist "C:\Users\horac\Documents\python_standalone\python.exe" (
    "C:\Users\horac\Documents\python_standalone\python.exe" bot_traductor.py
) else (
    python bot_traductor.py
)
pause
