# 📅 SINCRONIZACIÓN AUTOMÁTICA DIARIA A LAS 10:00

## 🎯 ¿Qué he configurado?

He configurado todo el sistema para que se ejecute **automáticamente todos los días a las 10:00 AM** sin que tengas que hacer nada. Tu ordenador solo necesita estar encendido a esa hora.

---

## 🚀 PASOS QUE TIENES QUE HACER TÚ (Solo una vez)

### 1️⃣ Instalar KOReader en tu Kobo
```bash
# Ver instrucciones completas:
python src/koreader_sync.py --setup
```

**Resumen rápido:**
- Descarga KOReader desde: https://github.com/koreader/koreader/releases
- Busca el archivo para Kobo (ej: `koreader-kobo-*.zip`)
- Descomprime y copia la carpeta `.adds/koreader/` a tu Kobo
- Reinicia el Kobo

### 2️⃣ Configurar servidor WebDAV (RECOMENDADO: Nextcloud)
- Crea cuenta gratuita en Nextcloud: https://nextcloud.com/signup/
- Anota tus credenciales:
  - URL: `https://tu-servidor.nextcloud.com/remote.php/webdav/`
  - Usuario: tu usuario de Nextcloud
  - Contraseña: tu contraseña de Nextcloud

### 3️⃣ Configurar KOReader para sincronizar
**En tu Kobo con KOReader:**
1. Settings (⚙️) → Network → Cloud Storage
2. Seleccionar "WebDAV"
3. Configurar con tus credenciales de Nextcloud
4. Activar: ✅ Enable sync, ✅ Sync documents annotations
5. Probar con "Test connection" → debe decir "Success"

### 4️⃣ Configurar el proyecto (Automático)
```bash
# Ejecuta el configurador interactivo:
python configure_koreader.py
```

**El configurador hará automáticamente:**
- ✅ Te pedirá tus credenciales WebDAV
- ✅ Probará la conexión
- ✅ Configurará la tarea programada de Windows
- ✅ Lo dejará todo listo para funcionar a las 10:00

---

## 🔄 CÓMO FUNCIONA LA SINCRONIZACIÓN DIARIA

### ⏰ **Horario fijo: 10:00 AM todos los días**

```
📱 KOReader (tu Kobo) → 🌐 WebDAV → ⏰ 10:00 AM → 💻 Tu PC → 📝 Notion
```

### 📅 **Rutina diaria automática:**

1. **Durante el día**: Lees y haces anotaciones en KOReader
2. **KOReader sincroniza**: Las anotaciones se suben automáticamente a WebDAV
3. **10:00 AM**: Tu PC se despierta y ejecuta la sincronización
4. **Resultado**: Las anotaciones aparecen en Notion automáticamente

### 💤 **¿Qué pasa si el PC está apagado a las 10:00?**

**No problem!** La tarea programada tiene configuración inteligente:
- Si el PC está apagado a las 10:00, la tarea se ejecutará **cuando lo enciendas**
- Windows detecta que se "perdió" la tarea y la ejecuta automáticamente
- Las anotaciones se van acumulando en WebDAV mientras tanto

---

## 🛠️ COMANDOS ÚTILES (Por si acaso)

### Probar que todo funciona:
```bash
python src/koreader_sync.py --test
```

### Sincronización manual (una vez):
```bash
python src/koreader_sync.py --sync-once
```

### Reconfigurar si algo falla:
```bash
python configure_koreader.py
```

### Ver el estado de la tarea programada:
```bash
# Abrir "Programador de tareas" y buscar: "KOReader Cloud Sync Daily 10AM"
taskschd.msc
```

---

## 📊 VERIFICACIÓN FINAL

### ✅ Checklist de que todo está configurado:

1. **KOReader instalado**: ✅ Aparece en el menú del Kobo
2. **WebDAV configurado**: ✅ "Test connection" en KOReader dice "Success"  
3. **Proyecto configurado**: ✅ `python src/koreader_sync.py --test` dice "✅ Conexión exitosa"
4. **Tarea programada**: ✅ Aparece en Task Scheduler como "KOReader Cloud Sync Daily 10AM"

### 🎯 **Si todo está ✅, ya no tienes que hacer nada más**

---

## 🔍 LOGS Y MONITOREO

### Ver qué pasó en la última sincronización:
```bash
# El archivo de log se crea automáticamente:
type koreader_sync.log
```

### Ejemplo de log exitoso:
```
2024-11-13 10:00:01 - INFO - 🔍 Verificando actualizaciones en KOReader...
2024-11-13 10:00:03 - INFO - 📁 Encontrados 3 archivos de sync
2024-11-13 10:00:05 - INFO - 📚 Procesados 2 libros con datos de sync  
2024-11-13 10:00:07 - INFO - 💾 SQLite creado: data/KoboReader_koreader_1699873207.sqlite
2024-11-13 10:00:15 - INFO - ✅ Sincronización con Notion completada
```

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### ❌ "Error de conexión WebDAV"
- Verifica credenciales en el archivo `.env`
- Prueba acceder a tu Nextcloud desde el navegador
- Re-ejecuta: `python configure_koreader.py`

### ❌ "No se encontraron datos de sincronización"
- Asegúrate de haber sincronizado desde KOReader al menos una vez
- En KOReader: Settings → Cloud Storage → "Sync now"
- Verifica que hay anotaciones/highlights en tus libros

### ❌ "La tarea programada no se ejecuta"
- Abre Task Scheduler (taskschd.msc)
- Busca "KOReader Cloud Sync Daily 10AM"  
- Clic derecho → "Ejecutar" para probar manualmente
- Verifica que esté habilitada y configurada para tu usuario

---

## 🎉 RESULTADO FINAL

**Una vez configurado todo:**

1. **Lees en tu Kobo** → KOReader sincroniza automáticamente
2. **Todos los días a las 10:00** → Tu PC procesa las anotaciones  
3. **Las anotaciones aparecen en Notion** → Sin hacer nada más

**¡Nunca más cables! 🔌❌**