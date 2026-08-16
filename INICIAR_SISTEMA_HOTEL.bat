@echo off
title TalkIA PRO - Servidor Web Hotel & Concierge
color 0B
echo ========================================================
echo   Iniciando Servidor Web del Hotel (TalkIA PRO)
echo ========================================================
echo.
cd /d "%~dp0"

set PYTHON_PATH="C:\Users\horac\Documents\TalkIA PRO Cursor\.venv-tradcodex\Scripts\python.exe"

if exist %PYTHON_PATH% (
    %PYTHON_PATH% servidor_talia.py
) else (
    python servidor_talia.py
)

pause
