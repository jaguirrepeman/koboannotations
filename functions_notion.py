def create_books(df, notion, NOTION_BOOKS_DATABASE_ID):
    books = df[['Autor', 'Título']].drop_duplicates()
    for _, row in books.iterrows():
        notion.pages.create(
            parent={"database_id": NOTION_BOOKS_DATABASE_ID},
            properties={
                "Título": {"title": [{"text": {"content": row['Título']}}]},
                "Autor": {"rich_text": [{"text": {"content": row['Autor']}}]},
            }
        )

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

def create_annotations(df, notion, NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID):

    last_date_in_notion = get_last_annotation_date_notion(NOTION_ANNOTATIONS_DATABASE_ID)
    # Filtrar las filas del DataFrame para incluir solo las nuevas anotaciones
    if last_date_in_notion:
        df = df[df['Fecha de creación'] > last_date_in_notion]

    for _, row in df.iterrows():
        notion.pages.create(
            parent={"database_id": NOTION_ANNOTATIONS_DATABASE_ID},
            properties={
                "Texto": {"title": [{"text": {"content": row['Texto']}}]},
                "Anotación": {"rich_text": [{"text": {"content": row['Anotación']}}]},
                # "Tipo": {"select": {"name": row['Tipo']}},
                "Tipo": {"multi_select": [{"name": option} for option in row['Tipo'].split(", ")]},
                "Capítulo": {"rich_text": [{"text": {"content": row['Capítulo']}}]},
                "Progreso del libro": {"number": row['Progreso del libro']},
                "Fecha de creación": {"date": {"start": row['Fecha de creación']}},
                "Libro": {"relation": [{"id": get_book_id(row['Título'], notion, NOTION_BOOKS_DATABASE_ID)}]}
            }
        )

def create_book_pages(df, notion, NOTION_BOOKS_DATABASE_ID, clear_content=False):
    grouped = df.groupby('Título')  # Agrupa por el título

    for título, group in grouped:
        # Ordena las anotaciones por 'Progreso del libro'
        group = group.sort_values(by='Progreso del libro')

        # Obtén el ID del libro existente
        try:
            book_id = get_book_id(título, notion, NOTION_BOOKS_DATABASE_ID)
        except ValueError:
            print(f"No se encontró el libro '{título}' en la base de datos. Skipping...")
            continue

        # Eliminar contenido existente si clear_content es True
        if clear_content:
            try:
                # Obtén los bloques existentes y elimínalos
                response = notion.blocks.children.list(block_id=book_id)
                for block in response['results']:
                    notion.blocks.delete(block['id'])
                print(f"Contenido existente eliminado para el libro '{título}'.")
            except Exception as e:
                print(f"Error al eliminar contenido existente para el libro '{título}': {e}")

        # Crear contenido estructurado y ordenado por capítulos
        chapter_blocks = []
        for chapter, chapter_group in group.groupby('Capítulo'):
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
                                    "content": f"{row['Texto']} ({row['Tipo']})",
                                },
                            }
                        ]
                    },
                }
                chapter_blocks.append(annotation_block)

        # Dividir bloques en fragmentos de máximo 100
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