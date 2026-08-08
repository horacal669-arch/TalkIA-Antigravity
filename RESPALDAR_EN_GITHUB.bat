@echo off
title TalkIA Antigravity - Respaldar en GitHub
color 0B
echo ========================================================
echo   Respaldando Proyecto TalkIA Antigravity en GitHub
echo ========================================================
echo.
cd /d "%~dp0"

REM Agregar Git al PATH temporal si esta en PortableGit
if exist "C:\Users\horac\Documents\PortableGit\cmd\git.exe" (
    set "PATH=C:\Users\horac\Documents\PortableGit\cmd;%PATH%"
)

echo 📌 Inicializando repositorio...
git init
git branch -M main

echo 📌 Agregando todos los archivos del proyecto...
git add .

echo 📌 Guardando cambios (Commit)...
git commit -m "TalkIA Antigravity - Version Profesional Comercial Completa con Multi-IA, Bot y Dashboards"

echo 📌 Conectando con GitHub (horacal669-arch/TalkIA-Antigravity)...
git remote remove origin 2>nul
git remote add origin https://github.com/horacal669-arch/TalkIA-Antigravity.git

echo 📌 Subiendo a GitHub (Push)...
git push -u origin main

echo.
echo ========================================================
echo ✅ ¡PROYECTO RESPALDADO CON ÉXITO EN GITHUB!
echo Repositorio: https://github.com/horacal669-arch/TalkIA-Antigravity
echo ========================================================
echo.
pause
