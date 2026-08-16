@echo off
title TalkIA PRO - Bot Traductor Personal
color 0A
echo ========================================================
echo    Iniciando Bot Traductor Personal Standalone (Telegram)
echo ========================================================
echo.
cd /d "%~dp0"

set PYTHON_PATH="C:\Users\horac\Documents\TalkIA PRO Cursor\.venv-tradcodex\Scripts\python.exe"

if exist %PYTHON_PATH% (
    %PYTHON_PATH% bot_traductor.py
) else (
    python bot_traductor.py
)

pause
