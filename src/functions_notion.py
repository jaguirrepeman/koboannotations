import pandas as pd
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tqdm import tqdm

# Función para limpiar los géneros en una lista
def clean_generos_list(generos):
    # Asegúrate de que generos no sea None y que cada elemento sea una cadena válida
    return [genero.replace(",", " ") if genero is not None else "" for genero in generos]

def create_book_hash(row):
    """Crear hash del contenido del libro para detectar cambios"""
    book_data = {
        'titulo': str(row.get('titulo', '')),
        'autor': str(row.get('autor', '')), 
        'generos': str(row.get('generos', '')),
        'estado': str(row.get('estado', '')),
        'fecha_publicacion': str(row.get('fecha_publicacion', '')),
        'fecha_ultima_lectura': str(row.get('fecha_ultima_lectura', '')),
        'paginas': str(row.get('paginas', '')),
        'num_anotaciones': str(row.get('num_anotaciones', '')),
        'idioma': str(row.get('idioma', ''))
    }
    return hashlib.md5(json.dumps(book_data, sort_keys=True).encode()).hexdigest()

def ensure_database_properties(notion, database_id, required_properties):
    """Asegura que la base de datos tenga las propiedades necesarias"""
    try:
        database = notion.databases.retrieve(database_id=database_id)
        existing_properties = database.get("properties", {})
        
        properties_to_add = {}
        for prop_name, prop_config in required_properties.items():
            if prop_name not in existing_properties:
                properties_to_add[prop_name] = prop_config
        
        if properties_to_add:
            notion.databases.update(
                database_id=database_id,
                properties=properties_to_add
            )
            print(f"✅ Campos añadidos automáticamente: {', '.join(properties_to_add.keys())}")
    
    except Exception as e:
        print(f"⚠️ No se pudieron añadir campos automáticamente: {e}")

def create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID, force_update=False):
    """
    Crear/actualizar libros en Notion
    
    Args:
        libros_df: DataFrame con información de libros
        notion: Cliente de Notion
        NOTION_BOOKS_DATABASE_ID: ID de la base de datos
        force_update: Si True, actualiza todos los libros ignorando el hash
    """
    # Asegurar que existan los campos necesarios
    required_props = {
        "Data_Hash": {"rich_text": {}},
        "Content_Hash": {"rich_text": {}}
    }
    ensure_database_properties(notion, NOTION_BOOKS_DATABASE_ID, required_props)
    
    # Obtener TODOS los libros existentes con paginación optimizada
    print("🔍 Cargando libros existentes de Notion...")
    existing_books = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": NOTION_BOOKS_DATABASE_ID,
            "page_size": 100  # Máximo tamaño de página para mejor performance
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        existing_books.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    print(f"   📚 Total de libros en Notion: {len(existing_books)}")

    existing_books_dict = {}
    existing_books_hash = {}
    books_to_delete = {}
    existing_completion_dates = {}

    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""

    # Mapear libros existentes con sus hashes
    for page in existing_books:
        if "Título" in page["properties"] and "Autor" in page["properties"]:
            try:
                title = page["properties"]["Título"]["title"]
                author = page["properties"]["Autor"]["rich_text"]
                
                # Obtener fecha de finalización de forma segura
                completion_date_prop = page["properties"].get("Fecha de finalización", {})
                completion_date = None
                if completion_date_prop and isinstance(completion_date_prop, dict):
                    date_value = completion_date_prop.get("date")
                    if date_value and isinstance(date_value, dict):
                        completion_date = date_value.get("start")
                
                if title and author:
                    book_key = (
                        normalize_text(title[0]["text"]["content"]),
                        normalize_text(author[0]["text"]["content"])
                    )
                    if book_key in existing_books_dict:
                        books_to_delete[page["id"]] = book_key  # Duplicados a eliminar
                    else:
                        existing_books_dict[book_key] = page["id"]
                        if completion_date:
                            existing_completion_dates[book_key] = completion_date
                        
                        # Obtener hash existente si está disponible
                        hash_prop = page["properties"].get("Data_Hash", {}).get("rich_text", [])
                        existing_hash = hash_prop[0]["text"]["content"] if hash_prop else ""
                        existing_books_hash[book_key] = existing_hash
            except (IndexError, KeyError, TypeError) as e:
                continue

    # Eliminar duplicados
    if books_to_delete:
        print(f"🗑️ Eliminando {len(books_to_delete)} libros duplicados...")
        for book_id in books_to_delete:
            try:
                notion.pages.update(**{"page_id": book_id, "archived": True})
            except Exception as e:
                print(f"⚠️ Error eliminando duplicado: {e}")

    books_created = 0
    books_updated = 0
    books_skipped = 0

    def process_book(row_tuple):
        """Procesa un libro individual (para paralelización)"""
        idx, row = row_tuple
        try:
            book_key = (
                normalize_text(row["titulo"]),
                normalize_text(row["autor"])
            )
            
            # Crear hash del libro actual
            current_hash = create_book_hash(row)
            
            # Verificar si el libro existe y si ha cambiado (o si forzamos actualización)
            if book_key in existing_books_dict:
                existing_hash = existing_books_hash.get(book_key, "")
                if not force_update and current_hash == existing_hash:
                    return "skipped", book_key, None
            
            # Construir propiedades básicas
            properties = {
                "Título": {"title": [{"text": {"content": row["titulo"]}}]},
                "Autor": {"rich_text": [{"text": {"content": row["autor"]}}]}
            }
            
            # Intentar añadir hash solo si el campo existe
            try:
                properties["Data_Hash"] = {"rich_text": [{"text": {"content": current_hash}}]}
            except:
                pass  # Si el campo no existe, continúa sin hash

            if isinstance(row.get("generos"), list) and len([g for g in row["generos"] if g is not None]) > 0:
                properties["Género"] = {"multi_select": [{"name": option} for option in row["generos"]]}

            if pd.notna(row.get("estado")):
                properties["Estado"] = {"status": {"name": row["estado"]}}
            if pd.notna(row.get("tiempo_lectura")):
                properties["Tiempo de lectura"] = {"rich_text": [{"text": {"content": row["tiempo_lectura"]}}]}
            if pd.notna(row.get("fecha_ultima_lectura")):
                properties["Fecha de última lectura"] = {"date": {"start": row["fecha_ultima_lectura"]}}
            if pd.notna(row.get("fecha_publicacion")):
                properties["Fecha de publicación"] = {"date": {"start": row["fecha_publicacion"]}}
            if pd.notna(row.get("paginas")):
                properties["Páginas"] = {"number": int(row['paginas'])}
            if pd.notna(row.get("num_anotaciones")):
                properties["Número de anotaciones"] = {"number": int(row['num_anotaciones'])}
            if pd.notna(row.get("idioma")):
                properties["Idioma"] = {"select": {"name": row['idioma']}}

            if book_key in existing_books_dict:
                # Verificar que no sea un libro recién creado en esta ejecución
                page_id = existing_books_dict[book_key]
                if page_id != "pending":
                    # Actualizar libro existente
                    # Preservar fecha de finalización existente o establecer nueva si es necesario
                    if row.get("estado") == "Leído":
                        # Si ya existe una fecha de finalización, preservarla
                        if book_key in existing_completion_dates:
                            properties["Fecha de finalización"] = {"date": {"start": existing_completion_dates[book_key]}}
                        # Si no existe pero el libro está finalizado, usar fecha_ultima_lectura
                        elif pd.notna(row.get("fecha_ultima_lectura")):
                            properties["Fecha de finalización"] = {"date": {"start": row["fecha_ultima_lectura"]}}
                    else:
                        # Limpiar la fecha de finalización si el libro no está finalizado
                        properties["Fecha de finalización"] = {"date": None}
                    
                    def _update():
                        return notion.pages.update(
                            **{
                                "page_id": page_id,
                                "properties": properties,
                            }
                        )
                    retry_api_call(_update, max_retries=3, initial_delay=1)
                    return "updated", book_key, None
                else:
                    # Ya se procesó en esta ejecución, saltar
                    return "skipped", book_key, None
            else:
                # Crear nuevo libro
                # Solo establecer fecha de finalización si el estado es "Leído"
                if row.get("estado") == "Leído" and pd.notna(row.get("fecha_ultima_lectura")):
                    properties["Fecha de finalización"] = {"date": {"start": row["fecha_ultima_lectura"]}}
                
                def _create():
                    return notion.pages.create(
                        parent={"database_id": NOTION_BOOKS_DATABASE_ID},
                        properties=properties,
                    )
                retry_api_call(_create, max_retries=3, initial_delay=1)
                return "created", book_key, None

        except Exception as e:
            return "error", None, f"Error procesando libro {row.get('titulo', 'desconocido')}: {e}"

    # Procesar libros en paralelo con barra de progreso
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_book, row_tuple) for row_tuple in libros_df.iterrows()]
        
        # Procesar resultados con barra de progreso
        for future in tqdm(as_completed(futures), total=len(futures), desc="📚 Sincronizando libros"):
            result, book_key, error = future.result()
            if result == "created":
                books_created += 1
                if book_key:
                    existing_books_dict[book_key] = "pending"
            elif result == "updated":
                books_updated += 1
            elif result == "skipped":
                books_skipped += 1
            elif result == "error" and error:
                print(f"\n❌ {error}")

    print(f"\n📚 Libros procesados: {books_created} creados, {books_updated} actualizados, {books_skipped} sin cambios")

def get_last_annotation_date_notion(notion, NOTION_ANNOTATIONS_DATABASE_ID):
    response = notion.databases.query(
        database_id=NOTION_ANNOTATIONS_DATABASE_ID,
        sorts=[{"property": "Fecha de creación", "direction": "descending"}],
        page_size=1  # Solo necesitamos la entrada más reciente
    )

    # Determinar la última fecha registrada
    if response['results']:
        last_date_in_notion = response['results'][0]['properties']['Fecha de creación']['date']['start']
    else:
        last_date_in_notion = None
    
    return last_date_in_notion
def retry_api_call(func, max_retries=3, initial_delay=1):
    """Reintentar llamadas a la API con backoff exponencial"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e)
            # Reintentar solo en errores temporales
            if any(code in error_str for code in ['502', '503', '504', '429', 'timeout', 'timed out']):
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"⏳ Error temporal ({error_str[:50]}...), reintentando en {delay}s... (intento {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    # Último intento fallido
                    raise
            else:
                # Error no recuperable, lanzar inmediatamente
                raise
    return None

def get_book_ids_batch(book_titles, notion, NOTION_BOOKS_DATABASE_ID):
    """Obtener IDs de libros en batch para evitar múltiples consultas"""
    cache = {}
    cache_normalized = {}
    
    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""
    
    # Obtener TODOS los libros con paginación optimizada
    all_books = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": NOTION_BOOKS_DATABASE_ID,
            "page_size": 100  # Máximo tamaño de página
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        all_books.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    # Crear cache con títulos originales y normalizados
    for page in all_books:
        try:
            title_prop = page["properties"].get("Título", {}).get("title", [])
            if title_prop:
                title = title_prop[0]["text"]["content"]
                cache[title] = page["id"]
                # También guardar versión normalizada para búsqueda flexible
                cache_normalized[normalize_text(title)] = page["id"]
        except (IndexError, KeyError):
            continue
    
    return cache, cache_normalized

def get_existing_annotation_ids(notion, NOTION_ANNOTATIONS_DATABASE_ID):
    """Obtener IDs únicos de anotaciones ya existentes en Notion"""
    existing_ids = set()
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": NOTION_ANNOTATIONS_DATABASE_ID,
            "page_size": 100
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        
        for page in response["results"]:
            try:
                # Obtener el ID único de la anotación
                id_prop = page["properties"].get("Annotation_ID", {}).get("rich_text", [])
                if id_prop:
                    existing_ids.add(id_prop[0]["text"]["content"])
            except (IndexError, KeyError):
                continue
        
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    return existing_ids

def create_annotation_id(row):
    """Crear ID único para cada anotación basado en sus atributos"""
    # Usar todo el texto en lugar de solo 100 caracteres para evitar colisiones
    annotation_data = f"{row['Título']}|{row['Capítulo']}|{row['Texto']}|{row['Progreso del libro']}"
    return hashlib.md5(annotation_data.encode()).hexdigest()

def create_annotations(df, notion, NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID):
    # Asegurar que exista el campo Annotation_ID en la base de datos
    required_props = {
        "Annotation_ID": {"rich_text": {}}
    }
    ensure_database_properties(notion, NOTION_ANNOTATIONS_DATABASE_ID, required_props)
    
    # Crear IDs únicos para todas las anotaciones del DataFrame
    df = df.copy()
    df['Annotation_ID'] = df.apply(create_annotation_id, axis=1)
    
    # Eliminar duplicados dentro del DataFrame primero
    df_unique = df.drop_duplicates(subset=['Annotation_ID'], keep='first')
    duplicates_in_df = len(df) - len(df_unique)
    if duplicates_in_df > 0:
        print(f"🔄 Eliminados {duplicates_in_df} duplicados dentro del DataFrame")
    
    # Obtener IDs de anotaciones ya existentes en Notion
    print("🔍 Verificando anotaciones existentes en Notion...")
    existing_ids = get_existing_annotation_ids(notion, NOTION_ANNOTATIONS_DATABASE_ID)
    
    # Filtrar solo las anotaciones nuevas (que no existen en Notion)
    df_new = df_unique[~df_unique['Annotation_ID'].isin(existing_ids)]
    
    print(f"📝 {len(existing_ids)} anotaciones en Notion, {len(df_unique)} únicas en Kobo, procesando {len(df_new)} nuevas")
    
    if len(df_new) == 0:
        print("✅ No hay anotaciones nuevas que procesar")
        return

    # Obtener IDs de libros en batch para eficiencia
    book_ids_cache, book_ids_normalized = get_book_ids_batch(df_new['Título'].unique(), notion, NOTION_BOOKS_DATABASE_ID)
    
    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""
    
    annotations_created = 0
    annotations_failed = 0
    
    # Preparar datos para procesamiento en batch
    annotations_to_create = []
    
    for _, row in df_new.iterrows():
        # Intentar búsqueda exacta primero
        book_id = book_ids_cache.get(row['Título'])
        
        # Si no encuentra, intentar búsqueda normalizada
        if not book_id:
            book_id = book_ids_normalized.get(normalize_text(row['Título']))
        
        if not book_id:
            print(f"⚠️ Libro no encontrado: {row['Título']}")
            annotations_failed += 1
            continue

        # Limitar texto para evitar errores de Notion
        texto = str(row['Texto'])[:2000] if pd.notna(row['Texto']) else ""
        anotacion = str(row['Anotación'])[:2000] if pd.notna(row['Anotación']) else ""
        
        annotations_to_create.append({
            "parent": {"database_id": NOTION_ANNOTATIONS_DATABASE_ID},
            "properties": {
                "Texto": {"title": [{"text": {"content": texto}}]},
                "Anotación": {"rich_text": [{"text": {"content": anotacion}}]},
                "Tipo": {"multi_select": [{"name": option} for option in str(row['Tipo']).split(", ")]},
                "Capítulo": {"rich_text": [{"text": {"content": str(row['Capítulo'])}}]},
                "Progreso del libro": {"number": float(row['Progreso del libro'])},
                "Fecha de creación": {"date": {"start": row['Fecha de creación']}},
                "Libro": {"relation": [{"id": book_id}]},
                "Annotation_ID": {"rich_text": [{"text": {"content": row['Annotation_ID']}}]}
            }
        })
    
    # Crear anotaciones en paralelo con threading (mucho más rápido)
    errors = []  # Almacenar errores para análisis
    
    if annotations_to_create:
        print(f"📝 Creando {len(annotations_to_create)} anotaciones en paralelo...")
        
        def create_annotation(annotation_data):
            def _create():
                return notion.pages.create(**annotation_data)
            
            try:
                retry_api_call(_create, max_retries=3, initial_delay=1)
                return (True, None)
            except Exception as e:
                return (False, str(e))
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_annotation, ann) for ann in annotations_to_create]
            
            # Usar tqdm para mostrar progreso
            with tqdm(total=len(annotations_to_create), desc="Creando anotaciones", unit="anotación") as pbar:
                for future in as_completed(futures):
                    success, error = future.result()
                    if success:
                        annotations_created += 1
                    else:
                        annotations_failed += 1
                        if error and error not in errors:
                            errors.append(error)
                    pbar.update(1)

    # Reporte final con estado apropiado
    total = annotations_created + annotations_failed
    if annotations_failed == 0:
        print(f"✅ {annotations_created} anotaciones creadas exitosamente")
    elif annotations_created == 0:
        print(f"❌ ERROR: No se pudo crear ninguna anotación ({annotations_failed} fallos)")
    else:
        print(f"⚠️ PARCIAL: {annotations_created} creadas, {annotations_failed} fallidas (tasa éxito: {annotations_created/total*100:.1f}%)")
    
    # Mostrar errores únicos si hay fallos
    if errors:
        print(f"\n🔍 Tipos de error detectados ({len(errors)} únicos):")
        for i, error in enumerate(errors[:3], 1):  # Mostrar hasta 3 errores diferentes
            print(f"   {i}. {error[:100]}...")  # Truncar errores largos
        if len(errors) > 3:
            print(f"   ... y {len(errors)-3} tipos más")

def create_content_hash(group):
    """Crear hash del contenido de anotaciones para detectar cambios"""
    content_str = ""
    for _, row in group.sort_values('Progreso del libro').iterrows():
        content_str += f"{row['Capítulo']}|{row['Texto']}|{row['Progreso del libro']}|"
    return hashlib.md5(content_str.encode()).hexdigest()

def get_existing_content_hash(notion, book_id):
    """Obtener hash de contenido existente del libro"""
    try:
        page = notion.pages.retrieve(page_id=book_id)
        hash_prop = page["properties"].get("Content_Hash", {}).get("rich_text", [])
        return hash_prop[0]["text"]["content"] if hash_prop else ""
    except:
        return ""  # Si no existe el campo o hay error, asume que no hay hash

def update_content_hash(notion, book_id, content_hash):
    """Actualizar hash en las propiedades del libro"""
    try:
        notion.pages.update(
            page_id=book_id,
            properties={"Content_Hash": {"rich_text": [{"text": {"content": content_hash}}]}}
        )
    except Exception as e:
        # Si falla (ej: campo no existe), continúa sin el hash
        pass

def clear_book_annotations(notion, book_id):
    """Limpiar solo las anotaciones del libro, preservando el resumen si existe"""
    try:
        # Obtener todos los bloques
        response = notion.blocks.children.list(block_id=book_id, page_size=100)
        blocks = response.get('results', [])
        
        # Buscar el divisor "--- ANOTACIONES ---" o similar
        # Todo lo que está después del divisor son anotaciones y se puede borrar
        # Todo lo que está antes es el resumen y se preserva
        
        separator_found = False
        blocks_to_delete = []
        
        for block in blocks:
            # Buscar el divisor
            block_type = block.get('type')
            if block_type == 'divider':
                separator_found = True
                blocks_to_delete.append(block['id'])  # También borrar el divisor
                continue
            
            # Si ya encontramos el separador, todo lo demás son anotaciones
            if separator_found:
                blocks_to_delete.append(block['id'])
        
        # Si no hay separador, borrar todo (comportamiento por defecto)
        if not separator_found:
            blocks_to_delete = [block['id'] for block in blocks]
        
        # Eliminar bloques en paralelo
        if blocks_to_delete:
            def delete_block(block_id):
                try:
                    notion.blocks.delete(block_id=block_id)
                    return True
                except:
                    return False
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(delete_block, bid) for bid in blocks_to_delete]
                for future in as_completed(futures):
                    future.result()
        
        return True
    except Exception as e:
        return False

def clear_book_content(notion, book_id):
    """Limpiar contenido existente del libro"""
    try:
        response = notion.blocks.children.list(block_id=book_id)
        for block in response['results']:
            notion.blocks.delete(block['id'])
    except Exception as e:
        print(f"⚠️ Error limpiando contenido: {e}")

def get_books_info_batch(book_titles, notion, NOTION_BOOKS_DATABASE_ID):
    """Obtener IDs y hashes de contenido de libros en batch para evitar múltiples consultas"""
    books_info = {}
    
    # Obtener todos los libros con paginación optimizada
    all_books = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": NOTION_BOOKS_DATABASE_ID,
            "page_size": 100  # Máximo tamaño de página
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        all_books.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    for page in all_books:
        try:
            title_prop = page["properties"].get("Título", {}).get("title", [])
            if title_prop:
                title = title_prop[0]["text"]["content"]
                
                # Obtener hash de contenido si existe
                hash_prop = page["properties"].get("Content_Hash", {}).get("rich_text", [])
                content_hash = hash_prop[0]["text"]["content"] if hash_prop else ""
                
                # Obtener estado del campo Resumen
                resumen_prop = page["properties"].get("Resumen", {})
                resumen_status = None
                if resumen_prop:
                    # Puede ser select o status dependiendo del tipo de campo
                    if "select" in resumen_prop and resumen_prop["select"]:
                        resumen_status = resumen_prop["select"].get("name")
                    elif "status" in resumen_prop and resumen_prop["status"]:
                        resumen_status = resumen_prop["status"].get("name")
                
                books_info[title] = {
                    "id": page["id"],
                    "content_hash": content_hash,
                    "resumen_status": resumen_status
                }
        except (IndexError, KeyError):
            continue
    
    return books_info

def create_book_pages(df, notion, NOTION_BOOKS_DATABASE_ID, force_update=False):
    """
    Actualizar contenido de páginas de libros
    
    Args:
        df: DataFrame con anotaciones
        notion: Cliente de Notion
        NOTION_BOOKS_DATABASE_ID: ID de la base de datos
        force_update: Si True, actualiza todos los libros ignorando el hash (excepto los que tienen Resumen="Listo")
    """
    # Agrupar por el título del libro
    grouped = df.groupby('Título', sort=False)
    
    pages_created = 0
    pages_skipped = 0
    pages_updated = 0

    # Obtener información de todos los libros en una sola consulta (optimización crítica)
    print("🔍 Obteniendo información de libros...")
    books_info = get_books_info_batch(grouped.groups.keys(), notion, NOTION_BOOKS_DATABASE_ID)
    
    def process_single_book(book_data):
        """Procesar un libro completo de forma secuencial"""
        título, group = book_data
        
        # Ordenar las anotaciones de forma precisa
        # Primero por progreso del libro, luego por capítulo (para mantener orden dentro del mismo progreso)
        # Si existe 'Fecha de creación', también se puede usar como criterio de desempate
        sort_columns = ['Progreso del libro', 'Capítulo']
        if 'Fecha de creación' in group.columns:
            sort_columns.append('Fecha de creación')
        
        group = group.sort_values(by=sort_columns, kind="stable")

        # Obtener el ID y hash del libro desde el caché
        book_info = books_info.get(título)
        if not book_info:
            return {"status": "not_found", "title": título}
        
        book_id = book_info["id"]
        existing_hash = book_info["content_hash"]
        resumen_status = book_info.get("resumen_status")
        
        # No procesar si el campo Resumen está en "Listo"
        if resumen_status == "Listo":
            return {"status": "skipped", "title": título}

        # Crear hash del contenido actual
        current_hash = create_content_hash(group)
        
        # Solo procesar si el contenido ha cambiado (o si se fuerza la actualización)
        if not force_update and current_hash == existing_hash:
            return {"status": "skipped", "title": título}
        
        try:
            # Si el resumen está "En progreso", solo limpiar las anotaciones (preservar resumen)
            # Si está vacío o en otro estado, limpiar todo
            if resumen_status == "En progreso":
                clear_book_annotations(notion, book_id)
            else:
                clear_book_content(notion, book_id)

            # Crear contenido estructurado por capítulos
            chapter_blocks = []
            
            # Si hay resumen en progreso, añadir divisor antes de las anotaciones
            if resumen_status == "En progreso":
                chapter_blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            
            current_chapter = None
            
            for _, row in group.iterrows():
                chapter = row['Capítulo']
                
                # Nuevo capítulo
                if chapter != current_chapter:
                    chapter_blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": f"Capítulo: {chapter}"}}]
                        }
                    })
                    current_chapter = chapter

                # Añadir anotación
                texto = str(row['Texto'])[:2000] if pd.notna(row['Texto']) else ""
                annotation_block = {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": texto
                                }
                            }
                        ]
                    }
                }
                chapter_blocks.append(annotation_block)

            # Dividir en chunks y añadir contenido SECUENCIALMENTE para este libro
            chunks = split_into_chunks(chapter_blocks, 100)
            
            for chunk in chunks:
                def _append():
                    return notion.blocks.children.append(
                        block_id=book_id,
                        children=chunk
                    )
                retry_api_call(_append, max_retries=3, initial_delay=1)
            
            # Actualizar hash de contenido
            def _update_hash():
                return update_content_hash(notion, book_id, current_hash)
            retry_api_call(_update_hash, max_retries=3, initial_delay=1)
            
            if existing_hash:
                return {"status": "updated", "title": título}
            else:
                return {"status": "created", "title": título}
                
        except Exception as e:
            return {"status": "error", "title": título, "error": str(e)}
    
    # Procesar LIBROS en paralelo (cada libro se procesa secuencialmente)
    print(f"📖 Procesando {len(grouped)} libros en paralelo...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_book, item) for item in grouped]
        
        # Usar tqdm para mostrar progreso
        with tqdm(total=len(grouped), desc="Procesando libros", unit="libro") as pbar:
            for future in as_completed(futures):
                result = future.result()
                
                if result["status"] == "created":
                    pages_created += 1
                elif result["status"] == "updated":
                    pages_updated += 1
                elif result["status"] == "skipped":
                    pages_skipped += 1
                
                pbar.update(1)

    print(f"📚 Páginas procesadas: {pages_created} creadas, {pages_updated} actualizadas, {pages_skipped} sin cambios")

def split_into_chunks(blocks, max_length):
    """
    Divide una lista de bloques en fragmentos más pequeños.

    Args:
        blocks (list): Lista de bloques a dividir.
        max_length (int): Longitud máxima permitida para cada fragmento.

    Returns:
        list: Lista de fragmentos de bloques.
    """
    return [blocks[i:i + max_length] for i in range(0, len(blocks), max_length)]

def create_markdown_content(group):
    content = []
    for _, row in group.iterrows():
        content.append(f"- **Capítulo {row['Capítulo']} ({row['Progreso del libro']}%)**\n")
        content.append(f"  - {row['Texto']}\n")
    return "\n".join(content)

def get_book_id(title, notion, NOTION_BOOKS_DATABASE_ID):
    try:
        response = notion.databases.query(
            database_id=NOTION_BOOKS_DATABASE_ID,
            filter={"property": "Título", "title": {"equals": title}}
        )
        if response['results']:
            return response['results'][0]['id']
        else:
            raise ValueError(f"No se encontró el libro '{title}' en la base de datos.")
    except Exception as e:
        print(f"Error al buscar el libro '{title}': {e}")
        raise

def get_books_from_notion(notion, NOTION_BOOKS_DATABASE_ID):
    books = notion.databases.query(
        **{"database_id": NOTION_BOOKS_DATABASE_ID}
    )["results"]
    
    book_list = []
    
    for page in books:
        try:
            properties = page.get("properties", {})
            
            title = properties.get("Título", {}).get("title", [])
            author = properties.get("Autor", {}).get("rich_text", [])
            genres = properties.get("Género", {}).get("multi_select", [])
            status = properties.get("Estado", {}).get("status", {}).get("name")
            reading_time = properties.get("Tiempo de lectura", {}).get("rich_text", [])
            last_read = properties.get("Fecha de última lectura", {}).get("date", {}).get("start")
            pub_date = properties.get("Fecha de publicación", {}).get("date", {}).get("start")
            pages = properties.get("Páginas", {}).get("number")
            notes_count = properties.get("Número de anotaciones", {}).get("number")
            language = properties.get("Idioma", {}).get("select", {}).get("name")
            
            book_list.append({
                "titulo": title[0]["text"].get("content") if title else None,
                "autor": author[0]["text"].get("content") if author else None,
                "generos": [g.get("name") for g in genres if g.get("name")],
                "estado": status,
                "tiempo_lectura": reading_time[0]["text"].get("content") if reading_time else None,
                "fecha_ultima_lectura": last_read,
                "fecha_publicacion": pub_date,
                "paginas": pages,
                "num_anotaciones": notes_count,
                "idioma": language
            })
        except Exception as e:
            print(f"Error procesando el libro con ID {page.get('id', 'Desconocido')}: {e}")
            continue
    
    return pd.DataFrame(book_list)
