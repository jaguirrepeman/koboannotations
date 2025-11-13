@echo off
REM Script de configuración y prueba para KOReader Cloud Sync

echo 🧪 CONFIGURACIÓN Y PRUEBA KOREADER CLOUD SYNC
echo ==============================================
echo.

REM Verificar estructura del proyecto
if not exist "src\koreader_sync.py" (
    echo ❌ Error: Archivo src\koreader_sync.py no encontrado
    pause
    exit /b 1
)

echo 📋 Opciones disponibles:
echo.
echo 1. 📖 Ver instrucciones de configuración completas
echo 2. 🧪 Probar conexión WebDAV existente
echo 3. 🔄 Ejecutar sincronización única (sin servicio)
echo 4. ⚙️ Configurar variables de entorno
echo 5. 🚀 Iniciar servicio de monitoreo continuo
echo.

set /p choice="Selecciona una opción (1-5): "

if "%choice%"=="1" goto show_instructions
if "%choice%"=="2" goto test_connection
if "%choice%"=="3" goto sync_once
if "%choice%"=="4" goto configure_env
if "%choice%"=="5" goto start_service

echo ❌ Opción inválida
pause
exit /b 1

:show_instructions
echo.
echo 📖 MOSTRANDO INSTRUCCIONES COMPLETAS...
echo.
python src\koreader_sync.py --setup
echo.
pause
exit /b 0

:test_connection
echo.
echo 🧪 PROBANDO CONEXIÓN WEBDAV...
echo.
python src\koreader_sync.py --test
echo.
pause
exit /b 0

:sync_once
echo.
echo 🔄 EJECUTANDO SINCRONIZACIÓN ÚNICA...
echo.
python src\koreader_sync.py --sync-once
echo.
pause
exit /b 0

:configure_env
echo.
echo ⚙️ CONFIGURACIÓN DE VARIABLES DE ENTORNO
echo ========================================
echo.

if exist ".env" (
    echo 📄 Archivo .env existente encontrado.
    set /p overwrite="¿Quieres reconfigurarlo? (s/n): "
    if /i not "%overwrite%"=="s" goto end_configure
)

if not exist ".env" (
    if not exist ".env.template" (
        echo ❌ Error: .env.template no encontrado
        pause
        exit /b 1
    )
    
    echo 📋 Creando .env desde .env.template...
    copy ".env.template" ".env" >nul
)

echo.
echo 🌐 Configuración de KOReader WebDAV:
echo.
echo Necesitas las siguientes credenciales de tu servidor WebDAV:
echo - URL del servidor (ej: https://tu-nextcloud.com/remote.php/webdav/)
echo - Usuario
echo - Contraseña
echo.

set /p webdav_url="URL WebDAV: "
set /p webdav_user="Usuario: "
set /p webdav_pass="Contraseña: "

echo.
echo 💾 Guardando configuración en .env...

REM Crear archivo temporal con la nueva configuración
(
echo # Environment Variables Template
echo # Copy this file to .env and fill in your actual values
echo.
echo # Dropbox Configuration
echo APP_KEY=your_dropbox_app_key
echo APP_SECRET=your_dropbox_app_secret
echo.
echo # Notion Configuration
echo NOTION_API_TOKEN=your_notion_api_token
echo NOTION_BOOKS_DATABASE_ID=your_books_database_id
echo NOTION_ANNOTATIONS_DATABASE_ID=your_annotations_database_id
echo.
echo # SQLite Database Path
echo SQLITE_PATH=KoboReader.sqlite
echo.
echo # KOReader Cloud Sync
echo KOREADER_WEBDAV_URL=%webdav_url%
echo KOREADER_USERNAME=%webdav_user%
echo KOREADER_PASSWORD=%webdav_pass%
) > .env.tmp

move .env.tmp .env >nul

echo ✅ Configuración guardada en .env
echo.
echo ⚠️ IMPORTANTE: También necesitas configurar las credenciales de Notion y Dropbox en .env
echo.

set /p test_now="¿Quieres probar la conexión WebDAV ahora? (s/n): "
if /i "%test_now%"=="s" (
    echo.
    echo 🧪 Probando conexión...
    python src\koreader_sync.py --test
)

:end_configure
echo.
pause
exit /b 0

:start_service
echo.
echo 🚀 INICIANDO SERVICIO DE MONITOREO...
echo.
echo 💡 El servicio se ejecutará continuamente hasta que presiones Ctrl+C
echo 📁 Los logs se guardarán en koreader_sync.log
echo.

set /p confirm="¿Continuar? (s/n): "
if /i not "%confirm%"=="s" exit /b 0

python src\koreader_sync.py
pause
exit /b 0