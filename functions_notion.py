import pandas as pd
# Función para limpiar los géneros en una lista
def clean_generos_list(generos):
    # Asegúrate de que generos no sea None y que cada elemento sea una cadena válida
    return [genero.replace(",", " ") if genero is not None else "" for genero in generos]

def create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID):
    existing_books = notion.databases.query(
        **{"database_id": NOTION_BOOKS_DATABASE_ID}
    )["results"]

    existing_books_dict = {}
    books_to_delete = {}
    existing_completion_dates = {}

    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""

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
            except IndexError:
                continue

    for book_id in books_to_delete:
        notion.pages.update(**{"page_id": book_id, "archived": True})

    for _, row in libros_df.iterrows():
        try:
            book_key = (
                normalize_text(row["titulo"]),
                normalize_text(row["autor"])
            )
            properties = {
                "Título": {"title": [{"text": {"content": row["titulo"]}}]},
                "Autor": {"rich_text": [{"text": {"content": row["autor"]}}]},
            }

            if isinstance(row["generos"], list) and len([g for g in row["generos"] if g is not None]) > 0:
                properties["Género"] = {"multi_select": [{"name": option} for option in row["generos"]]}

            if pd.notna(row["estado"]):
                properties["Estado"] = {"status": {"name": row["estado"]}}
            if pd.notna(row["tiempo_lectura"]):
                properties["Tiempo de lectura"] = {"rich_text": [{"text": {"content": row["tiempo_lectura"]}}]}
            if pd.notna(row["fecha_ultima_lectura"]):
                properties["Fecha de última lectura"] = {"date": {"start": row["fecha_ultima_lectura"]}}
            if pd.notna(row["fecha_publicacion"]):
                properties["Fecha de publicación"] = {"date": {"start": row["fecha_publicacion"]}}
            if pd.notna(row["paginas"]):
                properties["Páginas"] = {"number": row['paginas']}
            if pd.notna(row["num_anotaciones"]):
                properties["Número de anotaciones"] = {"number": row['num_anotaciones']}
            if pd.notna(row["idioma"]):
                properties["Idioma"] = {"select": {"name": row['idioma']}}

            if book_key in existing_books_dict:
                if book_key in existing_completion_dates:
                    properties["Fecha de finalización"] = {"date": {"start": existing_completion_dates[book_key]}}
                notion.pages.update(
                    **{
                        "page_id": existing_books_dict[book_key],
                        "properties": properties,
                    }
                )
            else:
                if pd.notna(row["fecha_ultima_lectura"]):
                    properties["Fecha de finalización"] = {"date": {"start": row["fecha_ultima_lectura"]}}
                notion.pages.create(
                    parent={"database_id": NOTION_BOOKS_DATABASE_ID},
                    properties=properties,
                )

        except Exception as e:
            print(f"Fallo en {row["titulo"], row["autor"]}")
            print(e)

            import traceback
            print(traceback.format_exc())

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

import pandas as pd

def create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID):
    existing_books = notion.databases.query(
        **{"database_id": NOTION_BOOKS_DATABASE_ID}
    )["results"]

    existing_books_dict = {}
    books_to_delete = {}

    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""

    for page in existing_books:
        if "Título" in page["properties"] and "Autor" in page["properties"]:
            try:
                title = page["properties"]["Título"]["title"]
                author = page["properties"]["Autor"]["rich_text"]
                if title and author:
                    book_key = (
                        normalize_text(title[0]["text"]["content"]),
                        normalize_text(author[0]["text"]["content"])
                    )
                    if book_key in existing_books_dict:
                        books_to_delete[page["id"]] = book_key  # Duplicados a eliminar
                    else:
                        existing_books_dict[book_key] = page["id"]
            except IndexError:
                continue

    for book_id in books_to_delete:
        notion.pages.update(**{"page_id": book_id, "archived": True})

    for _, row in libros_df.iterrows():
        try:
            book_key = (
                normalize_text(row["titulo"]),
                normalize_text(row["autor"])
            )
            properties = {
                "Título": {"title": [{"text": {"content": row["titulo"]}}]},
                "Autor": {"rich_text": [{"text": {"content": row["autor"]}}]},
            }

            if isinstance(row["generos"], list) and len([g for g in row["generos"] if g is not None]) > 0:
                properties["Género"] = {"multi_select": [{"name": option} for option in row["generos"]]}

            if pd.notna(row["estado"]):
                properties["Estado"] = {"status": {"name": row["estado"]}}
            if pd.notna(row["tiempo_lectura"]):
                properties["Tiempo de lectura"] = {"rich_text": [{"text": {"content": row["tiempo_lectura"]}}]}
            if pd.notna(row["fecha_ultima_lectura"]):
                properties["Fecha de última lectura"] = {"date": {"start": row["fecha_ultima_lectura"]}}
            if pd.notna(row["fecha_publicacion"]):
                properties["Fecha de publicación"] = {"date": {"start": row["fecha_publicacion"]}}
            if pd.notna(row["paginas"]):
                properties["Páginas"] = {"number": row['paginas']}
            if pd.notna(row["num_anotaciones"]):
                properties["Número de anotaciones"] = {"number": row['num_anotaciones']}
            if pd.notna(row["idioma"]):
                properties["Idioma"] = {"select": {"name": row['idioma']}}

            if book_key in existing_books_dict:
                notion.pages.update(
                    **{
                        "page_id": existing_books_dict[book_key],
                        "properties": properties,
                    }
                )
            else:
                notion.pages.create(
                    parent={"database_id": NOTION_BOOKS_DATABASE_ID},
                    properties=properties,
                )

        except Exception as e:
            print(f"Fallo en {row["titulo"], row["autor"]}")
            print(e)

            import traceback
            print(traceback.format_exc())

def create_annotations(df, notion, NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID, delete_existing=False):
    if delete_existing:
        existing_annotations = notion.databases.query(
            **{"database_id": NOTION_ANNOTATIONS_DATABASE_ID}
        )["results"]
        for page in existing_annotations:
            notion.pages.update(**{"page_id": page["id"], "archived": True})

    last_date_in_notion = get_last_annotation_date_notion(notion, NOTION_ANNOTATIONS_DATABASE_ID)
    if last_date_in_notion:
        df = df[df['Fecha de creación'] > last_date_in_notion]

    for _, row in df.iterrows():
        notion.pages.create(
            parent={"database_id": NOTION_ANNOTATIONS_DATABASE_ID},
            properties={
                "Texto": {"title": [{"text": {"content": row['Texto']}}]},
                "Anotación": {"rich_text": [{"text": {"content": row['Anotación']}}]},
                "Tipo": {"multi_select": [{"name": option} for option in row['Tipo'].split(", ")]},
                "Capítulo": {"rich_text": [{"text": {"content": row['Capítulo']}}]},
                "Progreso del libro": {"number": row['Progreso del libro']},
                "Fecha de creación": {"date": {"start": row['Fecha de creación']}},
                "Libro": {"relation": [{"id": get_book_id(row['Título'], notion, NOTION_BOOKS_DATABASE_ID)}]}
            }
        )

def create_book_pages(df, notion, NOTION_BOOKS_DATABASE_ID, clear_content=False):
    # Agrupar por el título del libro
    grouped = df.groupby('Título', sort=False)  # Mantener el orden del DataFrame

    for título, group in grouped:
        # Ordenar las anotaciones por el orden original (o por una columna específica)
        group = group.sort_values(by=['Progreso del libro'], kind="stable")

        # Obtener el ID del libro existente en la base de datos de Notion
        try:
            book_id = get_book_id(título, notion, NOTION_BOOKS_DATABASE_ID)
        except ValueError:
            print(f"No se encontró el libro '{título}' en la base de datos. Skipping...")
            continue

        # Eliminar contenido existente si clear_content es True
        if clear_content:
            try:
                # Eliminar todos los bloques hijos existentes en el libro
                response = notion.blocks.children.list(block_id=book_id)
                for block in response['results']:
                    notion.blocks.delete(block['id'])
                print(f"Contenido existente eliminado para el libro '{título}'.")
            except Exception as e:
                print(f"Error al eliminar contenido existente para el libro '{título}': {e}")

        # Crear contenido estructurado y ordenado por capítulos
        chapter_blocks = []
        for chapter, chapter_group in group.groupby('Capítulo', sort=False):
            # Header del capítulo
            chapter_header = {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"Capítulo {chapter}"}}]
                }
            }
            chapter_blocks.append(chapter_header)

            # Añadir anotaciones del capítulo
            for _, row in chapter_group.iterrows():
                annotation_block = {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{row['Texto']}",
                                },
                            }
                        ]
                    },
                }
                chapter_blocks.append(annotation_block)

        # Dividir los bloques en fragmentos de máximo 100 (limitación de Notion)
        chunks = split_into_chunks(chapter_blocks, 100)

        # Añadir bloques en iteraciones
        for chunk in chunks:
            try:
                notion.blocks.children.append(
                    block_id=book_id,
                    children=chunk
                )
            except Exception as e:
                print(f"Error al añadir contenido al libro '{título}': {e}")

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
