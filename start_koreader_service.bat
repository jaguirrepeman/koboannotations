@echo off
REM Script para ejecutar KOReader Cloud Sync como servicio
REM Este archivo debe estar en la raíz del proyecto koboannotations

echo 🤖 Iniciando KOReader Cloud Sync Service...
echo.

REM Verificar que estamos en la carpeta correcta
if not exist "src\koreader_sync.py" (
    echo ❌ Error: No se encuentra src\koreader_sync.py
    echo Asegúrate de ejecutar este script desde la carpeta koboannotations
    pause
    exit /b 1
)

REM Verificar que existe el archivo .env
if not exist ".env" (
    echo ❌ Error: No se encuentra el archivo .env
    echo.
    echo 📋 Pasos para configurar:
    echo 1. Copia .env.template a .env
    echo 2. Edita .env con tus credenciales de KOReader WebDAV
    echo 3. Ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Configuración encontrada
echo 🚀 Iniciando servicio...
echo.
echo 💡 Para detener el servicio: presiona Ctrl+C
echo 📁 Los logs se guardan en: koreader_sync.log
echo.

REM Ejecutar el servicio de KOReader
python src\koreader_sync.py

echo.
echo 🛑 Servicio KOReader Cloud Sync detenido
pause