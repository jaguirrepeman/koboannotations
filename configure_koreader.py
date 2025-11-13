#!/usr/bin/env python3
"""
Configurador interactivo para KOReader Cloud Sync
"""

import os
import sys
from pathlib import Path

def main():
    print("""
    🛠️  CONFIGURADOR KOREADER CLOUD SYNC
    ====================================
    
    Este asistente te ayudará a configurar la sincronización automática
    con KOReader y WebDAV para que nunca más tengas que conectar cables.
    """)
    
    # Verificar estructura del proyecto
    if not Path('src/koreader_sync.py').exists():
        print("❌ Error: Este script debe ejecutarse desde la raíz del proyecto koboannotations")
        return
    
    # Verificar si ya existe configuración
    env_file = Path('.env')
    if env_file.exists():
        print("📄 Se encontró configuración existente en .env")
        overwrite = input("¿Quieres reconfigurar KOReader? (s/n): ").lower().strip()
        if overwrite != 's':
            print("🚫 Configuración cancelada")
            return
    
    print("\n📋 PASOS PARA CONFIGURAR KOREADER:")
    print("""
    1. 📱 Instalar KOReader en tu Kobo
    2. 🌐 Configurar servidor WebDAV (Nextcloud recomendado)  
    3. ⚙️ Configurar sync en KOReader
    4. 🔗 Configurar credenciales en este proyecto
    
    ¿Ya completaste los pasos 1-3? (s/n): """, end="")
    
    ready = input().lower().strip()
    
    if ready != 's':
        print("""
        📖 INSTRUCCIONES COMPLETAS:
        
        Para ver las instrucciones paso a paso ejecuta:
        python src/koreader_sync.py --setup
        
        Vuelve a ejecutar este configurador cuando hayas completado la instalación.
        """)
        return
    
    print("\n🌐 CONFIGURACIÓN WEBDAV:")
    
    # Recopilar información WebDAV
    print("\n¿Qué servidor WebDAV estás usando?")
    print("1. Nextcloud")
    print("2. ownCloud") 
    print("3. Otro servidor WebDAV")
    
    server_choice = input("Selecciona (1-3): ").strip()
    
    if server_choice == "1":
        print("\n📋 Para Nextcloud, necesitas:")
        print("- URL: https://tu-servidor.nextcloud.com/remote.php/webdav/")
        print("- Usuario de Nextcloud")
        print("- Contraseña de Nextcloud")
    elif server_choice == "2":
        print("\n📋 Para ownCloud, necesitas:")
        print("- URL: https://tu-servidor.owncloud.com/remote.php/webdav/")
        print("- Usuario de ownCloud")  
        print("- Contraseña de ownCloud")
    else:
        print("\n📋 Para otro servidor WebDAV, necesitas:")
        print("- URL completa del WebDAV")
        print("- Usuario")
        print("- Contraseña")
    
    print()
    webdav_url = input("URL WebDAV: ").strip()
    webdav_user = input("Usuario: ").strip()
    
    # Ocultar contraseña al escribirla
    import getpass
    webdav_pass = getpass.getpass("Contraseña: ")
    
    # Validar URL
    if not webdav_url.startswith('http'):
        print("⚠️ Advertencia: La URL debería empezar con https://")
    
    # Crear o actualizar .env
    create_env_file(webdav_url, webdav_user, webdav_pass)
    
    print("\n✅ Configuración guardada en .env")
    
    # Probar conexión
    print("\n🧪 Probando conexión WebDAV...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, 'src/koreader_sync.py', '--test'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and "✅ Conexión exitosa" in result.stdout:
            print("🎉 ¡Conexión exitosa!")
            
            # Preguntar si quiere ejecutar sync
            sync_now = input("\n¿Ejecutar sincronización ahora? (s/n): ").lower().strip()
            if sync_now == 's':
                print("🔄 Ejecutando sincronización...")
                subprocess.run([sys.executable, 'src/koreader_sync.py', '--sync-once'])
            
            # Configurar tarea programada automáticamente
            setup_task = input("\n¿Configurar tarea automática diaria a las 10:00? (s/n): ").lower().strip()
            if setup_task == 's':
                print("⚙️ Configurando tarea programada de Windows...")
                task_result = subprocess.run(['setup_windows_task_10am.bat'], 
                                           capture_output=True, text=True, shell=True)
                
                if task_result.returncode == 0:
                    print("✅ Tarea programada configurada exitosamente")
                    print("📅 La sincronización se ejecutará automáticamente todos los días a las 10:00")
                else:
                    print("⚠️ No se pudo configurar la tarea automática")
                    print("   Puedes configurarla manualmente ejecutando: setup_windows_task_10am.bat")
            
            print("""
            🚀 ¡CONFIGURACIÓN COMPLETA!
            
            ✅ Configurado para sincronizar automáticamente a las 10:00 AM
            
            Opciones disponibles:
            
            1. Ver si todo funciona:
               python src/koreader_sync.py --test
            
            2. Sincronización manual única:
               python src/koreader_sync.py --sync-once
            
            3. Configurar tarea automática (si no se hizo):
               .\setup_windows_task_10am.bat
            
            ✨ ¡Ya no necesitas cables para sincronizar tu Kobo!
            📅 La sincronización se ejecutará automáticamente cada día a las 10:00
            """)
            
        else:
            print("❌ Error de conexión")
            if result.stderr:
                print(f"Error: {result.stderr}")
            print("\n📖 Verifica tu configuración y prueba de nuevo")
            
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")

def create_env_file(webdav_url, username, password):
    """Crear archivo .env con la configuración"""
    
    # Leer .env existente si existe para preservar otras configuraciones
    existing_config = {}
    env_file = Path('.env')
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing_config[key] = value
    
    # Actualizar con nueva configuración KOReader
    existing_config['KOREADER_WEBDAV_URL'] = webdav_url
    existing_config['KOREADER_USERNAME'] = username
    existing_config['KOREADER_PASSWORD'] = password
    
    # Valores por defecto si no existen
    defaults = {
        'APP_KEY': 'your_dropbox_app_key',
        'APP_SECRET': 'your_dropbox_app_secret',
        'NOTION_API_TOKEN': 'your_notion_api_token',
        'NOTION_BOOKS_DATABASE_ID': 'your_books_database_id',
        'NOTION_ANNOTATIONS_DATABASE_ID': 'your_annotations_database_id',
        'SQLITE_PATH': 'KoboReader.sqlite'
    }
    
    for key, default_value in defaults.items():
        if key not in existing_config:
            existing_config[key] = default_value
    
    # Escribir .env
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write("# Environment Variables\n")
        f.write("# Generated by KOReader configurator\n\n")
        
        f.write("# Dropbox Configuration\n")
        f.write(f"APP_KEY={existing_config['APP_KEY']}\n")
        f.write(f"APP_SECRET={existing_config['APP_SECRET']}\n\n")
        
        f.write("# Notion Configuration\n")
        f.write(f"NOTION_API_TOKEN={existing_config['NOTION_API_TOKEN']}\n")
        f.write(f"NOTION_BOOKS_DATABASE_ID={existing_config['NOTION_BOOKS_DATABASE_ID']}\n")
        f.write(f"NOTION_ANNOTATIONS_DATABASE_ID={existing_config['NOTION_ANNOTATIONS_DATABASE_ID']}\n\n")
        
        f.write("# SQLite Database Path\n")
        f.write(f"SQLITE_PATH={existing_config['SQLITE_PATH']}\n\n")
        
        f.write("# KOReader Cloud Sync\n")
        f.write(f"KOREADER_WEBDAV_URL={existing_config['KOREADER_WEBDAV_URL']}\n")
        f.write(f"KOREADER_USERNAME={existing_config['KOREADER_USERNAME']}\n")
        f.write(f"KOREADER_PASSWORD={existing_config['KOREADER_PASSWORD']}\n")

if __name__ == "__main__":
    main()