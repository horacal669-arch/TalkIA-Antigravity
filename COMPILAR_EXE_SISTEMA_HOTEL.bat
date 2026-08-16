@echo off
title TalkIA PRO - Compilar Ejecutable EXE (Sistema Web Hotel)
color 0E
echo ========================================================
echo   Empaquetando Servidor Web del Hotel en EXE Standalone
echo ========================================================
echo.
cd /d "%~dp0"

set PYTHON_PATH="C:\Users\horac\Documents\TalkIA PRO Cursor\.venv-tradcodex\Scripts\python.exe"

if not exist %PYTHON_PATH% (
    set PYTHON_PATH=python
)

echo [1/2] Verificando PyInstaller...
%PYTHON_PATH% -m pip install pyinstaller

echo.
echo [2/2] Compilando Servidor Web del Hotel con archivos estaticos...
%PYTHON_PATH% -m PyInstaller --noconfirm --onedir --console --name "TalkIA_Hotel_Server" ^
  --add-data "index.html;." ^
  --add-data "panel.html;." ^
  --add-data "config.html;." ^
  --add-data "login.html;." ^
  --add-data "qr_generator.html;." ^
  servidor_talia.py

echo.
echo ========================================================
echo ¡COMPILACIÓN COMPLETADA EXITOSAMENTE!
echo El ejecutable independiente esta en: dist\TalkIA_Hotel_Server\TalkIA_Hotel_Server.exe
echo ========================================================
pause
