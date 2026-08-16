@echo off
title TalkIA PRO - Compilar Ejecutable EXE (Bot Traductor)
color 0B
echo ========================================================
echo   Empaquetando Bot Traductor en Ejecutable Standalone (.EXE)
echo ========================================================
echo.
cd /d "%~dp0"

set PYTHON_PATH="C:\Users\horac\Documents\TalkIA PRO Cursor\.venv-tradcodex\Scripts\python.exe"

if not exist %PYTHON_PATH% (
    set PYTHON_PATH=python
)

echo [1/2] Instalando PyInstaller en el entorno...
%PYTHON_PATH% -m pip install pyinstaller

echo.
echo [2/2] Generando ejecutable ejecutable autonomo...
%PYTHON_PATH% -m PyInstaller --noconfirm --onedir --console --name "TalkIA_Traductor" bot_traductor.py

echo.
echo ========================================================
echo ¡COMPILACIÓN COMPLETADA EXITOSAMENTE!
echo El ejecutable independiente esta en: dist\TalkIA_Traductor\TalkIA_Traductor.exe
echo Para entregar al cliente, solo copia la carpeta dist\TalkIA_Traductor y el config_traductor.json
echo ========================================================
pause
