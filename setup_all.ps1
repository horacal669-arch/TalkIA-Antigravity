# setup_all.ps1

# Permitir ejecución de scripts en esta sesión (solo temporal)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Ruta del proyecto
$projectRoot = "C:\Users\horac\Documents\Proyecto TalkIA PRO"
Set-Location $projectRoot

# ---------------------------------------------------
# 1️⃣ Instalar dependencias dentro del entorno virtual (solo la primera vez)
& ".venv\Scripts\python.exe" -m pip install --quiet moviepy gtts numpy

# ---------------------------------------------------
# 2️⃣ Generar video promocional
& ".venv\Scripts\python.exe" generate_promo_video.py

# ---------------------------------------------------
# 3️⃣ Descargar ngrok (solo la primera vez)
if (-not (Test-Path ".\ngrok.exe")) {
    Write-Host "Descargando ngrok..."
    Invoke-WebRequest -Uri "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip" -OutFile "ngrok.zip"
    Expand-Archive -Path "ngrok.zip" -DestinationPath "." -Force
    Remove-Item "ngrok.zip"
    Write-Host "ngrok descargado."
}

# ---------------------------------------------------
# 4️⃣ Configurar Ngrok con el token proporcionado
$ngrokToken = "3I1aBpv1tedXZNAmdWalWraNuxi_7dKcT9mvWJUitodTxJVtE"
.\ngrok.exe authtoken $ngrokToken

# ---------------------------------------------------
# 5️⃣ Iniciar túnel Share Localhost al puerto 5000 (en segundo plano)
Start-Process -FilePath ".\ngrok.exe" -ArgumentList "http 5000" -NoNewWindow -PassThru | Out-Null
Write-Host "Ngrok túnel iniciado (share localhost)."

# ---------------------------------------------------
# 6️⃣ Iniciar servidor Flask (servidor_talia.py) en segundo plano
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "servidor_talia.py" -NoNewWindow -PassThru | Out-Null
Write-Host "Servidor Flask iniciado en http://localhost:5000"

# ---------------------------------------------------
Write-Host "Todo listo. Usa la URL que aparece en la consola de ngrok para acceder desde cualquier dispositivo."
