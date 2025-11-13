"""
KOReader Cloud Sync - Sistema de sincronización inalámbrica para KOReader
"""

import requests
import json
import time
import schedule
import os
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import logging

class KOReaderCloudSync:
    """
    Sincronización automática usando KOReader + servidor WebDAV
    """
    
    def __init__(self, webdav_url: str, username: str, password: str):
        self.webdav_url = webdav_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.timeout = 30
        
        # Configurar logging
        self.setup_logging()
        
        # Configurar directorios
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        self.koreader_dir = self.data_dir / 'koreader_sync'
        self.koreader_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Configurar logging específico para KOReader sync"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('koreader_sync.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"{__name__}.KOReaderSync")
    
    @staticmethod
    def get_setup_instructions() -> str:
        """Instrucciones completas para configurar KOReader"""
        return """
        📱 INSTALACIÓN KOREADER EN KOBO:
        
        1. 📥 Descargar KOReader:
           - Ir a: https://github.com/koreader/koreader/releases
           - Descargar el archivo para Kobo (ej: koreader-kobo-*.zip)
           - NO descargar el "appimage" o versiones de otros dispositivos
        
        2. 💾 Instalar en Kobo:
           - Conectar Kobo al PC
           - Extraer el ZIP descargado
           - Copiar la carpeta .adds/koreader/ a la raíz del Kobo
           - Asegurarse de que la ruta quede: [Kobo]/.adds/koreader/
           - Expulsar y desconectar el Kobo de forma segura
           - Reiniciar el Kobo
        
        3. ✅ Verificar instalación:
           - En el menú principal del Kobo aparecerá "KOReader"
           - Abrir KOReader (la primera vez puede tardar)
           - Debería cargar la interfaz de KOReader
        
        🌐 CONFIGURAR SERVIDOR WEBDAV:
        
        Opción A - Nextcloud (RECOMENDADO):
        ═══════════════════════════════════════
        1. Crear cuenta gratuita en:
           - https://nextcloud.com/signup/ (2GB gratis)
           - O buscar proveedores: https://nextcloud.com/providers/
           
        2. Obtener credenciales WebDAV:
           - URL: https://tu-instancia.nextcloud.com/remote.php/webdav/
           - Usuario: tu_usuario_nextcloud
           - Contraseña: tu_contraseña_nextcloud
        
        Opción B - ownCloud:
        ═══════════════════════
        - Similar a Nextcloud
        - URL típica: https://tu-owncloud.com/remote.php/webdav/
        
        Opción C - Servidor propio (avanzado):
        ════════════════════════════════════════
        - Docker: docker run -d -p 7200:7200 koreader/kosync
        - O configurar servidor WebDAV con Apache/Nginx
        
        ⚙️ CONFIGURAR SYNC EN KOREADER:
        
        1. Abrir KOReader en el Kobo
        2. Ir a: Settings (⚙️) → Network → Cloud Storage
        3. Seleccionar "WebDAV"
        4. Configurar:
           - Server: https://tu-servidor.com/remote.php/webdav/
           - Username: tu_usuario
           - Password: tu_contraseña
           - Sync directory: /koreader_sync/ (por defecto está bien)
        
        5. Habilitar opciones de sincronización:
           ✅ Enable sync
           ✅ Sync documents progress 
           ✅ Sync documents annotations
           ✅ Auto sync every X minutes (recomendado: 30-60 min)
        
        6. 🧪 Probar conexión:
           - Pulsar "Test connection" → debería decir "Success"
           - Pulsar "Sync now" para hacer primera sincronización
        
        📋 CONFIGURAR EN EL PROYECTO:
        
        Añadir al archivo .env:
        KOREADER_WEBDAV_URL=https://tu-servidor.com/remote.php/webdav/
        KOREADER_USERNAME=tu_usuario
        KOREADER_PASSWORD=tu_contraseña
        
        ✅ VERIFICAR QUE FUNCIONA:
        
        1. Abrir un libro en KOReader
        2. Hacer una anotación o highlight
        3. Esperar sincronización automática (o forzar con "Sync now")
        4. Ejecutar: python src/koreader_sync.py --test
        5. Debería encontrar y mostrar la nueva anotación
        """
    
    def test_connection(self) -> bool:
        """Probar conexión WebDAV"""
        try:
            self.logger.info("🔍 Probando conexión WebDAV...")
            
            # Probar acceso básico al servidor
            response = self.session.request('PROPFIND', self.webdav_url, headers={
                'Depth': '1',
                'Content-Type': 'text/xml'
            })
            
            if response.status_code in [200, 207, 301]:
                self.logger.info("✅ Conexión WebDAV exitosa")
                
                # Probar carpeta de KOReader específicamente
                koreader_path = f"{self.webdav_url}/koreader"
                response = self.session.request('PROPFIND', koreader_path, headers={
                    'Depth': '1',
                    'Content-Type': 'text/xml'
                })
                
                if response.status_code in [200, 207]:
                    self.logger.info("✅ Carpeta KOReader encontrada")
                    return True
                elif response.status_code == 404:
                    self.logger.warning("⚠️ Carpeta KOReader no encontrada - puede crearse automáticamente")
                    return True
                else:
                    self.logger.warning(f"⚠️ Carpeta KOReader inaccesible: {response.status_code}")
                    return False
            else:
                self.logger.error(f"❌ Error de conexión WebDAV: {response.status_code}")
                self.logger.error(f"Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error probando conexión: {e}")
            return False
    
    def list_webdav_contents(self, path: str = "/koreader") -> List[Dict]:
        """Listar contenidos de una carpeta WebDAV"""
        try:
            url = f"{self.webdav_url}{path}"
            
            # PROPFIND request para listar contenidos
            propfind_body = '''<?xml version="1.0" encoding="utf-8" ?>
            <D:propfind xmlns:D="DAV:">
                <D:allprop/>
            </D:propfind>'''
            
            response = self.session.request('PROPFIND', url, 
                                          data=propfind_body,
                                          headers={
                                              'Depth': '1',
                                              'Content-Type': 'text/xml; charset=utf-8'
                                          })
            
            if response.status_code in [200, 207]:
                # Parsear respuesta XML (simplificado)
                contents = []
                lines = response.text.split('\n')
                
                for line in lines:
                    if '<D:href>' in line and '</D:href>' in line:
                        href = line.split('<D:href>')[1].split('</D:href>')[0]
                        if href.endswith('.lua') or 'progress' in href or 'metadata' in href:
                            contents.append({
                                'path': href,
                                'name': href.split('/')[-1],
                                'type': 'file'
                            })
                
                return contents
            else:
                self.logger.warning(f"⚠️ No se pudo listar contenido: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Error listando contenidos WebDAV: {e}")
            return []
    
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Descargar archivo desde WebDAV"""
        try:
            url = f"{self.webdav_url}{remote_path}"
            
            response = self.session.get(url, stream=True)
            
            if response.status_code == 200:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.logger.debug(f"📥 Descargado: {remote_path} → {local_path}")
                return True
            else:
                self.logger.warning(f"⚠️ Error descargando {remote_path}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error descargando {remote_path}: {e}")
            return False
    
    def download_sync_data(self) -> Dict:
        """Descargar y procesar datos de sincronización de KOReader"""
        try:
            self.logger.info("📥 Descargando datos de KOReader...")
            
            # Listar archivos en el directorio de sync de KOReader
            sync_files = self.list_webdav_contents("/koreader")
            
            if not sync_files:
                self.logger.warning("⚠️ No se encontraron archivos de sincronización")
                return {}
            
            self.logger.info(f"📁 Encontrados {len(sync_files)} archivos de sync")
            
            # Procesar archivos de progreso y metadatos
            books_data = {}
            
            for file_info in sync_files:
                if file_info['name'].endswith('.lua'):
                    # Descargar archivo
                    local_file = self.koreader_dir / file_info['name']
                    
                    if self.download_file(file_info['path'], local_file):
                        # Procesar contenido del archivo Lua
                        book_data = self.parse_lua_file(local_file)
                        
                        if book_data:
                            # Extraer nombre del libro del nombre del archivo
                            book_id = file_info['name'].replace('.lua', '')
                            books_data[book_id] = book_data
            
            self.logger.info(f"📚 Procesados {len(books_data)} libros con datos de sync")
            return self.convert_to_kobo_format(books_data)
            
        except Exception as e:
            self.logger.error(f"❌ Error descargando datos de sync: {e}")
            return {}
    
    def parse_lua_file(self, file_path: Path) -> Dict:
        """Parsear archivo Lua de KOReader (simplificado)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraer datos básicos del formato Lua de KOReader
            book_data = {
                'annotations': [],
                'progress': {},
                'metadata': {}
            }
            
            # Buscar patrones comunes en archivos de KOReader
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Buscar anotaciones (patrón simplificado)
                if 'highlight' in line.lower() and '{' in line:
                    # Extraer texto de highlight (muy simplificado)
                    if '"text"' in line:
                        try:
                            parts = line.split('"text"')[1]
                            if '=' in parts and '"' in parts:
                                text = parts.split('"')[1]
                                book_data['annotations'].append({
                                    'text': text,
                                    'type': 'highlight',
                                    'datetime': datetime.now(timezone.utc).isoformat()
                                })
                        except:
                            pass
                
                # Buscar progreso de lectura
                if 'percent_finished' in line:
                    try:
                        progress = float(line.split('=')[1].split(',')[0].strip())
                        book_data['progress']['percent'] = progress
                    except:
                        pass
                
                # Buscar metadatos del libro
                if 'title' in line.lower() and '=' in line:
                    try:
                        title = line.split('=')[1].strip().strip('"\'').strip(',')
                        book_data['metadata']['title'] = title
                    except:
                        pass
            
            return book_data
            
        except Exception as e:
            self.logger.error(f"❌ Error parseando archivo Lua {file_path}: {e}")
            return {}
    
    def convert_to_kobo_format(self, koreader_data: Dict) -> Dict:
        """Convertir datos de KOReader al formato esperado por el sistema"""
        converted_books = []
        converted_annotations = []
        
        for book_id, book_data in koreader_data.items():
            # Extraer información del libro
            metadata = book_data.get('metadata', {})
            progress = book_data.get('progress', {})
            
            book_info = {
                'VolumeID': book_id,
                'Title': metadata.get('title', f'Book_{book_id}'),
                'Attribution': metadata.get('author', 'Unknown'),
                'ReadStatus': 1 if progress.get('percent', 0) > 0 else 0,
                'PercentRead': progress.get('percent', 0)
            }
            converted_books.append(book_info)
            
            # Extraer anotaciones
            annotations = book_data.get('annotations', [])
            for i, ann in enumerate(annotations):
                converted_annotations.append({
                    'VolumeID': book_id,
                    'Text': ann.get('text', ''),
                    'Annotation': ann.get('note', ''),
                    'DateCreated': ann.get('datetime', ''),
                    'ChapterProgress': i + 1,  # Aproximación
                    'Type': 'highlight' if ann.get('type') == 'highlight' else 'note',
                    'BookTitle': book_info['Title'],
                    'StartContainerPath': f"chapter_{i+1}",
                    'BookmarkID': f"{book_id}_{i}"
                })
        
        return {
            'books': converted_books,
            'annotations': converted_annotations
        }
    
    def create_kobo_sqlite(self, data: Dict) -> Path:
        """Crear archivo SQLite compatible con el formato de Kobo"""
        timestamp = int(time.time())
        sqlite_path = self.data_dir / f'KoboReader_koreader_{timestamp}.sqlite'
        
        try:
            # Crear base de datos SQLite con esquema básico de Kobo
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Crear tabla content (libros)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    ContentID TEXT PRIMARY KEY,
                    ContentType INTEGER,
                    MimeType TEXT,
                    BookID TEXT,
                    BookTitle TEXT,
                    Title TEXT,
                    Attribution TEXT,
                    DateCreated TEXT,
                    DateLastRead TEXT,
                    ReadStatus INTEGER,
                    ___PercentRead INTEGER,
                    EpubType INTEGER
                )
            ''')
            
            # Crear tabla Bookmark (anotaciones)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Bookmark (
                    BookmarkID TEXT PRIMARY KEY,
                    VolumeID TEXT,
                    ContentID TEXT,
                    StartContainerPath TEXT,
                    Text TEXT,
                    Annotation TEXT,
                    DateCreated TEXT,
                    DateModified TEXT,
                    ChapterProgress REAL,
                    Type TEXT
                )
            ''')
            
            # Insertar libros
            books = data.get('books', [])
            for book in books:
                cursor.execute('''
                    INSERT OR REPLACE INTO content 
                    (ContentID, BookID, BookTitle, Title, Attribution, ReadStatus, ___PercentRead, ContentType, EpubType)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 6, -1)
                ''', (
                    book['VolumeID'],
                    book['VolumeID'], 
                    book['Title'],
                    book['Title'],
                    book['Attribution'],
                    book['ReadStatus'],
                    int(book['PercentRead'])
                ))
            
            # Insertar anotaciones
            annotations = data.get('annotations', [])
            for ann in annotations:
                cursor.execute('''
                    INSERT OR REPLACE INTO Bookmark
                    (BookmarkID, VolumeID, ContentID, StartContainerPath, Text, Annotation, 
                     DateCreated, ChapterProgress, Type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ann['BookmarkID'],
                    ann['VolumeID'],
                    ann['VolumeID'],
                    ann['StartContainerPath'],
                    ann['Text'],
                    ann['Annotation'],
                    ann['DateCreated'],
                    ann['ChapterProgress'],
                    ann['Type']
                ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"💾 SQLite creado: {sqlite_path}")
            self.logger.info(f"   📚 {len(books)} libros, 📝 {len(annotations)} anotaciones")
            
            return sqlite_path
            
        except Exception as e:
            self.logger.error(f"❌ Error creando SQLite: {e}")
            return None
    
    def update_main_sqlite_link(self, new_sqlite_path: Path):
        """Actualizar enlace al archivo SQLite más reciente"""
        try:
            main_sqlite = self.data_dir / 'KoboReader.sqlite'
            
            # Remover enlace anterior si existe
            if main_sqlite.exists():
                main_sqlite.unlink()
            
            # Crear copia (en Windows no se puede hacer symlink fácilmente)
            import shutil
            shutil.copy2(new_sqlite_path, main_sqlite)
            
            self.logger.info(f"🔗 SQLite principal actualizado: {main_sqlite}")
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando enlace SQLite: {e}")
    
    def check_and_sync(self) -> bool:
        """Verificar cambios y sincronizar si es necesario"""
        try:
            self.logger.info("🔍 Verificando actualizaciones en KOReader...")
            
            # Descargar datos actuales
            sync_data = self.download_sync_data()
            
            if not sync_data or (not sync_data.get('books') and not sync_data.get('annotations')):
                self.logger.info("✅ No hay datos nuevos de KOReader")
                return False
            
            books_count = len(sync_data.get('books', []))
            annotations_count = len(sync_data.get('annotations', []))
            
            self.logger.info(f"📚 Encontrados {books_count} libros")
            self.logger.info(f"📝 Encontradas {annotations_count} anotaciones")
            
            if books_count == 0 and annotations_count == 0:
                self.logger.info("✅ No hay contenido para sincronizar")
                return False
            
            # Crear SQLite compatible
            sqlite_path = self.create_kobo_sqlite(sync_data)
            
            if sqlite_path:
                # Actualizar enlace principal
                self.update_main_sqlite_link(sqlite_path)
                
                # Ejecutar sincronización principal
                self.execute_main_sync()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error en verificación y sync: {e}")
            return False
    
    def execute_main_sync(self):
        """Ejecutar el proceso principal de sincronización"""
        try:
            self.logger.info("⚡ Ejecutando sincronización completa con Notion...")
            
            # Ejecutar main.py
            import subprocess
            result = subprocess.run(['python', 'main.py'], 
                                  capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                self.logger.info("✅ Sincronización con Notion completada")
                if result.stdout:
                    self.logger.info(f"Output: {result.stdout}")
            else:
                self.logger.error("❌ Error en sincronización con Notion")
                if result.stderr:
                    self.logger.error(f"Error: {result.stderr}")
                    
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando main sync: {e}")
    
    def start_monitoring(self):
        """Iniciar monitoreo automático de cambios"""
        self.logger.info("🤖 Iniciando monitoreo de KOReader Cloud Sync...")
        
        # Programar verificación SOLO a las 10:00 diariamente
        schedule.every().day.at("10:00").do(self.check_and_sync)
        
        print(f"""
    🤖 KOREADER CLOUD SYNC ACTIVO
    
    ✅ Configuración:
    - Servidor WebDAV: {self.webdav_url}
    - Usuario: {self.username}
    - Verificación: diaria a las 10:00
    - Log: koreader_sync.log
    
    🔄 Programación:
    - 10:00 diario: sincronización automática
    
    📝 Para parar: Ctrl+C
    """)
        
        # Primera verificación inmediata
        print("🚀 Ejecutando primera verificación...")
        self.check_and_sync()
        
        # Loop principal
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto si hay tareas programadas
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Monitoreo detenido por el usuario")
        except Exception as e:
            self.logger.error(f"\n❌ Error en el servicio: {e}")

def main():
    """Función principal"""
    import argparse
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(description='KOReader Cloud Sync')
    parser.add_argument('--test', action='store_true', help='Probar conexión y salir')
    parser.add_argument('--sync-once', action='store_true', help='Sincronizar una vez y salir')
    parser.add_argument('--setup', action='store_true', help='Mostrar instrucciones de configuración')
    
    args = parser.parse_args()
    
    if args.setup:
        print(KOReaderCloudSync.get_setup_instructions())
        return
    
    # Cargar variables de entorno
    load_dotenv()
    
    webdav_url = os.getenv('KOREADER_WEBDAV_URL')
    username = os.getenv('KOREADER_USERNAME')
    password = os.getenv('KOREADER_PASSWORD')
    
    if not all([webdav_url, username, password]):
        print("❌ Faltan variables de entorno para KOReader:")
        print("   KOREADER_WEBDAV_URL")
        print("   KOREADER_USERNAME") 
        print("   KOREADER_PASSWORD")
        print("\n📖 Para ver instrucciones completas:")
        print("   python src/koreader_sync.py --setup")
        return
    
    # Crear instancia del sincronizador
    sync_service = KOReaderCloudSync(webdav_url, username, password)
    
    if args.test:
        print("🧪 PROBANDO CONEXIÓN KOREADER...")
        success = sync_service.test_connection()
        
        if success:
            print("✅ Conexión exitosa!")
            # Probar descarga de datos
            data = sync_service.download_sync_data()
            if data:
                books = len(data.get('books', []))
                annotations = len(data.get('annotations', []))
                print(f"📚 Encontrados {books} libros y {annotations} anotaciones")
            else:
                print("⚠️ No se encontraron datos de sincronización")
                print("   Asegúrate de haber sincronizado desde KOReader al menos una vez")
        else:
            print("❌ Error de conexión - revisar configuración")
        
        return
    
    if args.sync_once:
        print("🔄 SINCRONIZACIÓN ÚNICA...")
        success = sync_service.check_and_sync()
        
        if success:
            print("✅ Sincronización completada")
        else:
            print("⚠️ No hubo cambios para sincronizar")
        
        return
    
    # Iniciar monitoreo continuo
    sync_service.start_monitoring()

if __name__ == "__main__":
    main()