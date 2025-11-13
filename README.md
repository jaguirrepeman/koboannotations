# Kobo Annotations to Notion Sync

Este proyecto procesa las anotaciones de un e-reader Kobo y las sincroniza con bases de datos de Notion, incluyendo metadatos de libros desde Dropbox.

## 📁 Estructura del Proyecto

```
koboannotations/
├── src/                    # Código fuente principal
│   ├── __init__.py
│   ├── config.py          # Configuración y variables de entorno
│   ├── db_manager.py      # Manejo de la base de datos SQLite
│   ├── functions_dropbox.py  # Funciones para interactuar con Dropbox
│   ├── functions_epub.py  # Procesamiento de archivos EPUB
│   └── functions_notion.py   # Funciones para interactuar con Notion
├── notebooks/             # Notebooks de Jupyter para análisis
│   ├── notebook_kobo.ipynb
│   ├── notebook_kobo_desarrollo.ipynb
│   └── auth_dropbox.ipynb
├── data/                  # Archivos de datos
│   ├── *.sqlite          # Bases de datos de Kobo
│   ├── *.pkl            # Metadatos guardados
│   └── *.xlsx           # Archivos Excel
├── pruebas/              # Código de pruebas y experimentación
├── main.py              # Script principal
├── requirements.txt     # Dependencias de Python
├── .env.template       # Plantilla de variables de entorno
└── README.md           # Este archivo
```

## 🚀 Instalación y Configuración

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

1. Copia el archivo `.env.template` a `.env`:
   ```bash
   copy .env.template .env
   ```

2. Edita el archivo `.env` con tus credenciales:
   ```bash
   # Dropbox Configuration
   APP_KEY=tu_dropbox_app_key
   APP_SECRET=tu_dropbox_app_secret

   # Notion Configuration
   NOTION_API_TOKEN=tu_notion_api_token
   NOTION_BOOKS_DATABASE_ID=tu_books_database_id
   NOTION_ANNOTATIONS_DATABASE_ID=tu_annotations_database_id

   # SQLite Database Path
   SQLITE_PATH=KoboReader.sqlite
   ```

### 3. Preparar los datos

1. Copia tu base de datos de Kobo (`KoboReader.sqlite`) a la carpeta `data/`
2. Asegúrate de tener acceso a tu carpeta de Dropbox con los archivos EPUB

## 📖 Uso

### Ejecutar el script completo

```bash
python main.py
```

Este script ejecutará todo el proceso:
1. Carga datos de la base de datos de Kobo
2. Obtiene metadatos de libros desde Dropbox
3. Sincroniza libros con Notion
4. Sincroniza anotaciones con Notion
5. Crea páginas de libros con anotaciones estructuradas

### Usar los notebooks

Los notebooks en la carpeta `notebooks/` permiten análisis interactivo:

- `notebook_kobo.ipynb`: Notebook principal para procesamiento paso a paso
- `notebook_kobo_desarrollo.ipynb`: Notebook de desarrollo y experimentación
- `auth_dropbox.ipynb`: Notebook para configurar autenticación de Dropbox

## 🔧 Configuración de APIs

### Dropbox

1. Crea una aplicación en [Dropbox Developers](https://www.dropbox.com/developers/apps)
2. Obtén `APP_KEY` y `APP_SECRET`
3. Configura los permisos necesarios para acceder a archivos

### Notion

1. Crea una integración en [Notion Developers](https://www.notion.so/my-integrations)
2. Obtén el token de API (`NOTION_API_TOKEN`)
3. Crea dos bases de datos en Notion:
   - Una para libros con propiedades: Título, Autor, Género, Estado, etc.
   - Una para anotaciones con propiedades: Texto, Anotación, Tipo, Capítulo, etc.
4. Comparte las bases de datos con tu integración
5. Obtén los IDs de las bases de datos desde las URLs

## 🛠️ Funcionalidades Principales

### Procesamiento de Base de Datos Kobo
- Extrae anotaciones y highlights
- Procesa información de libros
- Maneja diferentes tipos de contenido (EPUB, otros formatos)

### Integración con Dropbox
- Descarga metadatos de archivos EPUB
- Procesa información de publicación, géneros, páginas
- Autenticación OAuth2 con tokens de refresco

### Sincronización con Notion (Optimizada)
- **Detección inteligente de cambios**: Solo actualiza libros que han cambiado usando hashes
- **Sincronización incremental**: Solo procesa anotaciones nuevas desde la última ejecución
- **Optimización de contenido**: Solo regenera páginas de libros si el contenido ha cambiado
- **Caché de consultas**: Obtiene IDs de libros en batch para mayor eficiencia
- **Métricas detalladas**: Muestra estadísticas de elementos creados/actualizados/omitidos

## ⚡ Optimizaciones de Eficiencia

El sistema implementa varias optimizaciones para reducir significativamente el tiempo de ejecución:

### Detección de Cambios
- **Hashes MD5**: Cada libro y página de contenido tiene un hash único
- **Solo actualiza si hay cambios**: Compara hashes para evitar actualizaciones innecesarias
- **Sincronización incremental**: Solo procesa anotaciones nuevas desde la última ejecución

### Métricas en Tiempo Real
```
📚 Libros procesados: 2 creados, 5 actualizados, 15 sin cambios
📝 Procesando 12 anotaciones nuevas desde 2024-11-10
📖 Páginas procesadas: 1 creadas, 2 actualizadas, 8 sin cambios
```

### Beneficios Esperados
- **Primera ejecución**: Tiempo completo (baseline)
- **Ejecuciones posteriores**: 70-90% menos tiempo si no hay muchos cambios
- **Solo anotaciones nuevas**: Procesamiento instantáneo si no hay libros nuevos

## 🔍 Troubleshooting

### Error de dependencias
```bash
pip install --upgrade -r requirements.txt
```

### Error de base de datos SQLite
- Verifica que el archivo `KoboReader.sqlite` esté en `data/`
- Asegúrate de que no esté siendo usado por otra aplicación

### Error de autenticación Dropbox
- Verifica que `APP_KEY` y `APP_SECRET` sean correctos
- Ejecuta el notebook `auth_dropbox.ipynb` para reautenticar

### Error de Notion API
- Verifica que el token sea válido
- Confirma que las bases de datos estén compartidas con la integración
- Verifica que los IDs de las bases de datos sean correctos

### Performance lenta
- Verifica tu conexión a internet
- Las primeras ejecuciones siempre tardan más
- Revisa que las bases de datos de Notion no tengan demasiados registros duplicados

## 📝 Personalización

El código está modularizado para facilitar la personalización:

- **`src/config.py`**: Configura variables de entorno y parámetros
- **`src/functions_notion.py`**: Personaliza la estructura de datos de Notion
- **`src/db_manager.py`**: Modifica las consultas SQL según tus necesidades
- **`main.py`**: Ajusta el flujo principal del proceso

## 🤝 Contribuciones

Este es un proyecto personal, pero las mejoras son bienvenidas. Por favor:

1. Mantén el código limpio y documentado
2. Prueba los cambios antes de enviar
3. Actualiza la documentación si es necesario

## 🏷️ Campos de Optimización (Automáticos)

El sistema **añade automáticamente** estos campos a tu base de datos de libros en Notion:
- `Data_Hash` (Rich Text) - detecta cambios en datos del libro
- `Content_Hash` (Rich Text) - detecta cambios en anotaciones

**✅ No requiere acción manual** - se crean automáticamente en la primera ejecución.

Si no se pueden crear automáticamente, el sistema funciona igual pero sin las optimizaciones de velocidad.

## 🤖 Sincronización Automática (KOReader)

### 📱 **Opción Inalámbrica Completa - KOReader + WebDAV**

Para sincronización **completamente automática** sin necesidad de conectar nunca el Kobo al PC:

#### 1. **Configuración Rápida**

```bash
# Ejecutar asistente de configuración
.\setup_koreader.bat
```

El asistente te guiará paso a paso para:
- Ver instrucciones completas de instalación
- Configurar credenciales WebDAV
- Probar la conexión
- Iniciar el servicio

#### 2. **Instalación Manual de KOReader**

Si prefieres hacerlo manualmente:

```bash
# Ver instrucciones detalladas
python src\koreader_sync.py --setup

# Probar conexión (después de configurar .env)
python src\koreader_sync.py --test

# Sincronizar una vez
python src\koreader_sync.py --sync-once

# Iniciar servicio continuo
python src\koreader_sync.py
```

#### 3. **Configuración Mínima Requerida**

Añade a tu archivo `.env`:

```bash
# KOReader Cloud Sync
KOREADER_WEBDAV_URL=https://tu-servidor-nextcloud.com/remote.php/webdav/
KOREADER_USERNAME=tu_usuario_webdav  
KOREADER_PASSWORD=tu_password_webdav
```

#### 4. **Servidores WebDAV Recomendados**

| Servicio | Gratuito | Configuración | Recomendación |
|----------|----------|---------------|---------------|
| **Nextcloud** | ✅ 2GB | Fácil | 🥇 **Mejor opción** |
| **ownCloud** | ✅ 2GB | Fácil | 🥈 Alternativa sólida |
| **Propio servidor** | ✅ Ilimitado | Avanzada | 🔧 Solo expertos |

**Nextcloud (recomendado):**
- Crear cuenta gratuita en: https://nextcloud.com/signup/
- URL: `https://tu-instancia.nextcloud.com/remote.php/webdav/`

#### 5. **Funcionalidades del Servicio Automático**

```
🤖 KOREADER CLOUD SYNC ACTIVO

✅ Configuración:
- Servidor WebDAV: https://tu-servidor.com/webdav/
- Verificación: cada hora + 8:00 y 20:00
- Log: koreader_sync.log

🔄 Programación:
- Cada hora: verificar actualizaciones
- 08:00 diario: sincronización matutina  
- 20:00 diario: sincronización nocturna

📝 Para parar: Ctrl+C
```

#### 6. **Flujo Automático Completo**

1. **En tu Kobo con KOReader:**
   - Lees un libro → haces highlights/anotaciones
   - KOReader sincroniza automáticamente cada 30-60 min
   - Datos se suben a tu servidor WebDAV

2. **En tu PC (automático):**
   - Servicio descarga cambios desde WebDAV cada hora
   - Convierte formato KOReader → formato Kobo
   - Ejecuta sincronización completa con Notion
   - Todo se actualiza automáticamente

3. **En Notion:**
   - Aparecen automáticamente nuevos libros y anotaciones
   - Páginas de libros se actualizan con nuevo contenido
   - Sin intervención manual necesaria

#### 7. **Ejecutar como Servicio de Windows**

Para que funcione **siempre en segundo plano**:

```bash
# Iniciar servicio
.\start_koreader_service.bat

# O configurar como servicio de Windows permanente
schtasks /create /tn "KoboSync" /tr "C:\ruta\start_koreader_service.bat" /sc onlogon
```

#### 8. **Resolución de Problemas**

```bash
# Probar conexión WebDAV
python src\koreader_sync.py --test

# Ver logs detallados
type koreader_sync.log

# Sincronización manual única
python src\koreader_sync.py --sync-once
```

**Problemas comunes:**
- **Error 401**: Credenciales WebDAV incorrectas
- **Error 404**: URL WebDAV incorrecta o carpeta koreader no existe
- **Sin datos**: KOReader no ha sincronizado aún desde el Kobo

### 📊 **Comparación de Métodos**

| Método | Cables | Configuración | Automatización | Recomendación |
|--------|--------|---------------|----------------|---------------|
| **Manual** | Siempre | Ninguna | ❌ | Solo ocasional |
| **KOReader + WebDAV** | Nunca | Una vez | ✅ Completa | 🥇 **Mejor opción** |

## ⚠️ Importante

- **Nunca** subas el archivo `.env` al control de versiones
- Mantén seguros tus tokens de API
- Haz copias de seguridad de tu base de datos de Kobo antes de procesarla
- El archivo de configuración original ha sido actualizado para usar variables de entorno por seguridad