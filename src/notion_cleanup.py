"""
Módulo para limpieza y mantenimiento de bases de datos de Notion.
Incluye funciones para eliminar duplicados y limpiar completamente las bases de datos.
"""
from notion_client import Client
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def remove_duplicate_books(notion, database_id):
    """
    Elimina libros duplicados de la base de datos de Notion.
    Mantiene solo la primera ocurrencia de cada libro (por título + autor).
    
    Args:
        notion: Cliente de Notion
        database_id: ID de la base de datos de libros
    
    Returns:
        dict: Estadísticas de la operación (total, duplicados, eliminados)
    """
    print("🔍 Buscando libros duplicados en Notion...")
    
    # Obtener TODOS los libros con paginación optimizada
    all_books = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": database_id,
            "page_size": 100  # Máximo tamaño de página
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        all_books.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    print(f"   📚 Total de libros en Notion: {len(all_books)}")
    
    # Detectar duplicados
    seen_books = {}
    duplicates = []
    
    def normalize_text(text):
        return text.strip().lower() if isinstance(text, str) else ""
    
    for page in all_books:
        try:
            if "Título" in page["properties"] and "Autor" in page["properties"]:
                title = page["properties"]["Título"]["title"]
                author = page["properties"]["Autor"]["rich_text"]
                
                if title and author:
                    book_key = (
                        normalize_text(title[0]["text"]["content"]),
                        normalize_text(author[0]["text"]["content"])
                    )
                    
                    if book_key in seen_books:
                        duplicates.append({
                            "id": page["id"],
                            "title": title[0]["text"]["content"],
                            "author": author[0]["text"]["content"]
                        })
                    else:
                        seen_books[book_key] = page["id"]
        except (IndexError, KeyError, TypeError):
            continue
    
    if not duplicates:
        print("✅ No se encontraron duplicados.")
        return {"total": len(all_books), "duplicates": 0, "deleted": 0}
    
    print(f"\n⚠️  Se encontraron {len(duplicates)} libros duplicados:")
    for i, dup in enumerate(duplicates[:5], 1):
        print(f"   {i}. {dup['title']} - {dup['author']}")
    if len(duplicates) > 5:
        print(f"   ... y {len(duplicates) - 5} más")
    
    # Eliminar duplicados en paralelo con alta concurrencia
    deleted_count = 0
    
    def delete_page(dup):
        try:
            notion.pages.update(**{"page_id": dup["id"], "archived": True})
            return True
        except Exception as e:
            return False
    
    # Usar 20 workers para máxima velocidad
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(delete_page, dup) for dup in duplicates]
        
        # Usar tqdm para mostrar progreso
        with tqdm(total=len(duplicates), desc="Eliminando duplicados", unit="libro") as pbar:
            for future in as_completed(futures):
                if future.result():
                    deleted_count += 1
                pbar.update(1)
    
    print(f"✅ Duplicados eliminados: {deleted_count}/{len(duplicates)}")
    
    return {
        "total": len(all_books),
        "duplicates": len(duplicates),
        "deleted": deleted_count
    }


def clear_notion_database(notion, database_id, database_name, confirm=True):
    """
    Elimina todos los registros de una base de datos de Notion.
    
    Args:
        notion: Cliente de Notion
        database_id: ID de la base de datos a limpiar
        database_name: Nombre descriptivo de la base de datos
        confirm: Si es True, pide confirmación antes de eliminar (default: True)
    
    Returns:
        int: Número de registros eliminados
    """
    print(f"\n🔍 Obteniendo todos los registros de {database_name}...")
    
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": database_id,
            "page_size": 100  # Máximo tamaño de página
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        all_pages.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    print(f"   📚 Total de registros encontrados: {len(all_pages)}")
    
    if len(all_pages) == 0:
        print(f"✅ La base de datos {database_name} ya está vacía.")
        return 0
    
    # Confirmar eliminación si es necesario
    if confirm:
        response = input(f"\n⚠️  ¿Estás seguro de eliminar {len(all_pages)} registros de {database_name}? (s/n): ")
        if response.lower() != 's':
            print(f"❌ Operación cancelada para {database_name}.")
            return 0
    
    # Eliminar todos los registros en paralelo con alta concurrencia
    deleted_count = 0
    failed_count = 0
    
    def delete_page(page):
        try:
            notion.pages.update(**{"page_id": page["id"], "archived": True})
            return True
        except Exception as e:
            return False
    
    print(f"🗑️  Eliminando {len(all_pages)} registros en paralelo...")
    
    # Usar 30 workers para máxima velocidad (Notion tiene límite de 3 req/sec por defecto, pero con muchos workers se compensa)
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(delete_page, page) for page in all_pages]
        
        # Usar tqdm para mostrar progreso
        with tqdm(total=len(all_pages), desc=f"🗑️  Eliminando", unit=" registros") as pbar:
            for future in as_completed(futures):
                if future.result():
                    deleted_count += 1
                else:
                    failed_count += 1
                pbar.update(1)
    
    print(f"✅ {database_name}: {deleted_count} registros eliminados, {failed_count} fallidos.")
    return deleted_count


def clean_all_notion_databases(notion, books_db_id, annotations_db_id, confirm=True):
    """
    Limpia completamente las bases de datos de libros y anotaciones en Notion.
    
    Args:
        notion: Cliente de Notion
        books_db_id: ID de la base de datos de libros
        annotations_db_id: ID de la base de datos de anotaciones
        confirm: Si es True, pide confirmación antes de eliminar (default: True)
    
    Returns:
        dict: Estadísticas de la operación (libros_eliminados, anotaciones_eliminadas)
    """
    print("=" * 60)
    print("🧹 LIMPIEZA COMPLETA DE BASES DE DATOS DE NOTION")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA: Esta operación eliminará TODOS los datos.")
    print("   - Base de datos de Libros")
    print("   - Base de datos de Anotaciones")
    print("\n💡 Después de la limpieza, sincroniza desde cero.")
    
    if confirm:
        response = input("\n¿Deseas continuar con la limpieza completa? (s/n): ")
        if response.lower() != 's':
            print("\n❌ Operación cancelada. No se eliminó ningún dato.")
            return {"books_deleted": 0, "annotations_deleted": 0}
    
    # Limpiar anotaciones primero (para evitar referencias rotas)
    annotations_deleted = clear_notion_database(
        notion, annotations_db_id, "Anotaciones", confirm=False
    )
    
    # Limpiar libros
    books_deleted = clear_notion_database(
        notion, books_db_id, "Libros", confirm=False
    )
    
    print("\n" + "=" * 60)
    print("✨ Limpieza completada. Las bases de datos están vacías.")
    print("=" * 60)
    
    return {
        "books_deleted": books_deleted,
        "annotations_deleted": annotations_deleted
    }


def clear_all_book_pages(notion, books_db_id, confirm=True):
    """
    Limpia el contenido (bloques) de todas las páginas de libros en Notion.
    No elimina los libros, solo el contenido dentro de cada página.
    
    Args:
        notion: Cliente de Notion
        books_db_id: ID de la base de datos de libros
        confirm: Si es True, pide confirmación antes de limpiar (default: True)
    
    Returns:
        int: Número de libros cuyas páginas fueron limpiadas
    """
    print("=" * 60)
    print("🧹 LIMPIEZA DE CONTENIDO DE PÁGINAS DE LIBROS")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA: Esta operación eliminará el CONTENIDO de todas las páginas de libros.")
    print("   - Se mantienen los libros en la base de datos")
    print("   - Solo se elimina el contenido interno (anotaciones)")
    
    if confirm:
        response = input("\n¿Deseas continuar con la limpieza? (s/n): ")
        if response.lower() != 's':
            print("\n❌ Operación cancelada.")
            return 0
    
    # Obtener TODOS los libros con paginación
    print("\n🔍 Obteniendo lista de libros...")
    all_books = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_params = {
            "database_id": books_db_id,
            "page_size": 100
        }
        if start_cursor:
            query_params["start_cursor"] = start_cursor
        
        response = notion.databases.query(**query_params)
        all_books.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    print(f"   📚 Total de libros: {len(all_books)}")
    
    if len(all_books) == 0:
        print("✅ No hay libros para limpiar.")
        return 0
    
    # Función para limpiar el contenido de un libro
    def clear_book_content(book_id):
        try:
            # Estrategia: Simplemente archivar todos los bloques hijos sin necesidad de listarlos
            # Notion borra automáticamente el contenido cuando archivas los bloques
            # Obtener solo los bloques de primer nivel (más rápido)
            response = notion.blocks.children.list(block_id=book_id, page_size=100)
            blocks = response.get('results', [])
            
            # Si no hay bloques, ya está vacío
            if not blocks:
                return True
            
            # Eliminar bloques en paralelo (solo primer nivel, los hijos se borran automáticamente)
            def delete_block(block_id):
                try:
                    notion.blocks.delete(block_id=block_id)
                    return True
                except:
                    return False
            
            with ThreadPoolExecutor(max_workers=10) as block_executor:
                block_futures = [block_executor.submit(delete_block, block['id']) for block in blocks]
                for future in as_completed(block_futures):
                    future.result()
            
            # Si había más de 100 bloques, repetir hasta que no queden más
            while response.get("has_more", False):
                response = notion.blocks.children.list(block_id=book_id, page_size=100)
                blocks = response.get('results', [])
                if blocks:
                    with ThreadPoolExecutor(max_workers=10) as block_executor:
                        block_futures = [block_executor.submit(delete_block, block['id']) for block in blocks]
                        for future in as_completed(block_futures):
                            future.result()
            
            return True
        except Exception as e:
            return False
    
    # Procesar libros en paralelo
    print(f"\n🗑️ Limpiando contenido de {len(all_books)} libros en paralelo...")
    
    cleaned_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(clear_book_content, book["id"]) for book in all_books]
        
        with tqdm(total=len(all_books), desc="Limpiando páginas", unit="libro") as pbar:
            for future in as_completed(futures):
                if future.result():
                    cleaned_count += 1
                else:
                    failed_count += 1
                pbar.update(1)
    
    print(f"✅ {cleaned_count} páginas limpiadas, {failed_count} fallidas.")
    print("=" * 60)
    
    return cleaned_count
