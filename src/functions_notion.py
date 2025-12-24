import pandas as pd
import hashlib
import json

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

def create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID):
    # Asegurar que existan los campos necesarios
    required_props = {
        "Data_Hash": {"rich_text": {}},
        "Content_Hash": {"rich_text": {}}
    }
    ensure_database_properties(notion, NOTION_BOOKS_DATABASE_ID, required_props)
    
    existing_books = notion.databases.query(
        **{"database_id": NOTION_BOOKS_DATABASE_ID}
    )["results"]

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
                completion_date = page["properties"].get("Fecha de finalización", {}).get("date", {}).get("start")
                
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
            except IndexError:
                continue

    # Eliminar duplicados
    for book_id in books_to_delete:
        notion.pages.update(**{"page_id": book_id, "archived": True})

    books_created = 0
    books_updated = 0
    books_skipped = 0

    for _, row in libros_df.iterrows():
        try:
            book_key = (
                normalize_text(row["titulo"]),
                normalize_text(row["autor"])
            )
            
            # Crear hash del libro actual
            current_hash = create_book_hash(row)
            
            # Verificar si el libro existe y si ha cambiado
            if book_key in existing_books_dict:
                existing_hash = existing_books_hash.get(book_key, "")
                if current_hash == existing_hash:
                    books_skipped += 1
                    continue  # No hay cambios, saltar
            
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
                # Actualizar libro existente
                if book_key in existing_completion_dates:
                    properties["Fecha de finalización"] = {"date": {"start": existing_completion_dates[book_key]}}
                notion.pages.update(
                    **{
                        "page_id": existing_books_dict[book_key],
                        "properties": properties,
                    }
                )
                books_updated += 1
            else:
                # Crear nuevo libro
                if pd.notna(row.get("fecha_ultima_lectura")):
                    properties["Fecha de finalización"] = {"date": {"start": row["fecha_ultima_lectura"]}}
                notion.pages.create(
                    parent={"database_id": NOTION_BOOKS_DATABASE_ID},
                    properties=properties,
                )
                books_created += 1

        except Exception as e:
            print(f"❌ Error procesando libro {row.get('titulo', 'desconocido')}: {e}")

    print(f"📚 Libros procesados: {books_created} creados, {books_updated} actualizados, {books_skipped} sin cambios")

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

def get_book_ids_batch(book_titles, notion, NOTION_BOOKS_DATABASE_ID):
    """Obtener IDs de libros en batch para evitar múltiples consultas"""
    cache = {}
    
    # Obtener todos los libros de una vez
    all_books = notion.databases.query(database_id=NOTION_BOOKS_DATABASE_ID)["results"]
    
    for page in all_books:
        try:
            title_prop = page["properties"].get("Título", {}).get("title", [])
            if title_prop:
                title = title_prop[0]["text"]["content"]
                cache[title] = page["id"]
        except (IndexError, KeyError):
            continue
    
    return cache

def create_annotations(df, notion, NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID):
    # Obtener fecha de la última anotación para procesar solo nuevas
    last_date_in_notion = get_last_annotation_date_notion(notion, NOTION_ANNOTATIONS_DATABASE_ID)
    
    if last_date_in_notion:
        df_new = df[pd.to_datetime(df['Fecha de creación']) > pd.to_datetime(last_date_in_notion)]
        print(f"📅 Procesando {len(df_new)} anotaciones nuevas desde {last_date_in_notion}")
    else:
        df_new = df
        print(f"📝 Procesando todas las {len(df_new)} anotaciones (primera vez)")
    
    if len(df_new) == 0:
        print("✅ No hay anotaciones nuevas que procesar")
        return

    # Obtener IDs de libros en batch para eficiencia
    book_ids_cache = get_book_ids_batch(df_new['Título'].unique(), notion, NOTION_BOOKS_DATABASE_ID)
    
    annotations_created = 0
    annotations_failed = 0

    for _, row in df_new.iterrows():
        try:
            book_id = book_ids_cache.get(row['Título'])
            if not book_id:
                print(f"⚠️ Libro no encontrado: {row['Título']}")
                annotations_failed += 1
                continue

            # Limitar texto para evitar errores de Notion
            texto = str(row['Texto'])[:2000] if pd.notna(row['Texto']) else ""
            anotacion = str(row['Anotación'])[:2000] if pd.notna(row['Anotación']) else ""
            
            notion.pages.create(
                parent={"database_id": NOTION_ANNOTATIONS_DATABASE_ID},
                properties={
                    "Texto": {"title": [{"text": {"content": texto}}]},
                    "Anotación": {"rich_text": [{"text": {"content": anotacion}}]},
                    "Tipo": {"multi_select": [{"name": option} for option in str(row['Tipo']).split(", ")]},
                    "Capítulo": {"rich_text": [{"text": {"content": str(row['Capítulo'])}}]},
                    "Progreso del libro": {"number": float(row['Progreso del libro'])},
                    "Fecha de creación": {"date": {"start": row['Fecha de creación']}},
                    "Libro": {"relation": [{"id": book_id}]}
                }
            )
            annotations_created += 1
            
        except Exception as e:
            print(f"❌ Error creando anotación: {e}")
            annotations_failed += 1

    print(f"✅ {annotations_created} anotaciones creadas, {annotations_failed} fallidas")

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

def clear_book_content(notion, book_id):
    """Limpiar contenido existente del libro"""
    try:
        response = notion.blocks.children.list(block_id=book_id)
        for block in response['results']:
            notion.blocks.delete(block['id'])
    except Exception as e:
        print(f"⚠️ Error limpiando contenido: {e}")

def create_book_pages(df, notion, NOTION_BOOKS_DATABASE_ID):
    # Agrupar por el título del libro
    grouped = df.groupby('Título', sort=False)
    
    pages_created = 0
    pages_skipped = 0
    pages_updated = 0

    for título, group in grouped:
        # Ordenar las anotaciones
        group = group.sort_values(by=['Progreso del libro'], kind="stable")

        # Obtener el ID del libro existente
        try:
            book_id = get_book_id(título, notion, NOTION_BOOKS_DATABASE_ID)
        except ValueError:
            print(f"❌ Libro '{título}' no encontrado en la base de datos")
            continue

        # Crear hash del contenido actual
        current_hash = create_content_hash(group)
        existing_hash = get_existing_content_hash(notion, book_id)
        
        # Solo procesar si el contenido ha cambiado
        if current_hash == existing_hash:
            print(f"⏩ Saltando '{título}' - sin cambios en anotaciones")
            pages_skipped += 1
            continue
            
        print(f"📖 Procesando contenido de '{título}'...")

        # Limpiar contenido existente
        clear_book_content(notion, book_id)

        # Crear contenido estructurado por capítulos
        chapter_blocks = []
        current_chapter = None
        
        for _, row in group.iterrows():
            chapter = row['Capítulo']
            
            # Nuevo capítulo
            if chapter != current_chapter:
                chapter_blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
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
                                "content": f"({row['Progreso del libro']}%) {texto}"
                            }
                        }
                    ]
                }
            }
            chapter_blocks.append(annotation_block)

        # Dividir en chunks y añadir contenido
        chunks = split_into_chunks(chapter_blocks, 100)
        for chunk in chunks:
            try:
                notion.blocks.children.append(
                    block_id=book_id,
                    children=chunk
                )
            except Exception as e:
                print(f"❌ Error añadiendo contenido al libro '{título}': {e}")
        
        # Actualizar hash de contenido
        update_content_hash(notion, book_id, current_hash)
        
        if existing_hash:
            pages_updated += 1
        else:
            pages_created += 1

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
