@echo off
REM Configurar tarea programada de Windows para KOReader Sync a las 10:00 AM
REM Este script configura el Task Scheduler de Windows para ejecutar automáticamente la sincronización

echo ========================================
echo   CONFIGURADOR DE TAREA PROGRAMADA
echo   KOReader Sync - Todos los dias 10:00 AM
echo ========================================
echo.

REM Obtener la ruta completa del directorio actual
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo Configurando tarea programada de Windows...
echo Directorio del proyecto: %PROJECT_DIR%
echo.

REM Crear la tarea programada usando schtasks
schtasks /create /tn "KOReader Cloud Sync Daily 10AM" /tr "\"%PROJECT_DIR%\start_koreader_daily_10am.bat\"" /sc daily /st 10:00 /f /ru "%USERNAME%"

if errorlevel 1 (
    echo.
    echo ❌ ERROR: No se pudo crear la tarea programada
    echo    Posibles causas:
    echo    - Necesitas permisos de administrador
    echo    - Ya existe una tarea con el mismo nombre
    echo.
    echo 💡 SOLUCION MANUAL:
    echo    1. Abre "Programador de tareas" (Task Scheduler)
    echo    2. Haz clic en "Crear tarea básica"
    echo    3. Nombre: KOReader Cloud Sync Daily 10AM
    echo    4. Desencadenador: Diariamente a las 10:00
    echo    5. Acción: Iniciar programa
    echo    6. Programa: %PROJECT_DIR%\start_koreader_daily_10am.bat
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ TAREA PROGRAMADA CREADA EXITOSAMENTE
echo.
echo 📋 Detalles de la configuración:
echo    Nombre: KOReader Cloud Sync Daily 10AM
echo    Horario: Todos los días a las 10:00 AM
echo    Usuario: %USERNAME%
echo    Comando: %PROJECT_DIR%\start_koreader_daily_10am.bat
echo.
echo 🔍 Para verificar la tarea:
echo    1. Abre "Programador de tareas" (taskschd.msc)
echo    2. Busca "KOReader Cloud Sync Daily 10AM"
echo.
echo ⚙️ Para modificar horario:
echo    1. Abre el Programador de tareas
echo    2. Busca la tarea "KOReader Cloud Sync Daily 10AM"
echo    3. Clic derecho → Propiedades → Desencadenadores
echo.
echo 🗑️ Para eliminar la tarea:
echo    schtasks /delete /tn "KOReader Cloud Sync Daily 10AM" /f
echo.

REM Mostrar información de la tarea creada
echo 📊 INFORMACIÓN DE LA TAREA:
schtasks /query /tn "KOReader Cloud Sync Daily 10AM" /fo list

echo.
echo ========================================
echo Configuración completada
echo ========================================
pause