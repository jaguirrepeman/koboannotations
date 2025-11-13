@echo off
REM Iniciar servicio de KOReader Cloud Sync - Solo a las 10:00 AM
REM Este script debe ejecutarse automáticamente al iniciar Windows

echo ========================================
echo   KOREADER CLOUD SYNC - SERVICIO DIARIO
echo   Sincronizacion automatica a las 10:00
echo ========================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"
echo Directorio de trabajo: %CD%
echo.

REM Verificar que existe Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en PATH
    echo Instala Python o agregalo al PATH del sistema
    pause
    exit /b 1
)

REM Verificar que existe el archivo de configuracion
if not exist ".env" (
    echo ERROR: Archivo .env no encontrado
    echo Ejecuta primero: python configure_koreader.py
    pause
    exit /b 1
)

REM Verificar que existen las dependencias
python -c "import schedule, requests, dotenv" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Faltan dependencias Python
    echo Instalando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
)

echo ✅ Configuracion verificada
echo ⏰ Iniciando servicio de sincronizacion diaria (10:00 AM)...
echo 📝 Log: koreader_sync.log
echo.
echo Para detener el servicio: Ctrl+C
echo Para ver el log: type koreader_sync.log
echo ========================================
echo.

REM Ejecutar el servicio de sincronizacion
python src/koreader_sync.py

REM Si llega aqui, el servicio se detuvo
echo.
echo ========================================
echo Servicio de KOReader Cloud Sync detenido
echo ========================================
pause