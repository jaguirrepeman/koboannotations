import os
import pandas as pd
from notion_client import Client
from src.functions_dropbox import manage_epub_metadata
from src.functions_notion import create_books, create_annotations, create_book_pages
from src.data_processor import process_data
from src.db_manager import SQLiteWrapper
from src.config import NOTION_API_TOKEN, NOTION_BOOKS_DATABASE_ID, NOTION_ANNOTATIONS_DATABASE_ID

def main():
    """
    Sincroniza las anotaciones de Kobo con Notion de forma incremental.
    """
    # --- 1. Carga de datos desde la BBDD de Kobo ---
    print("📖 Cargando datos desde Kobo...")
    db_path = os.path.join("data", "KoboReader.sqlite")
    db = SQLiteWrapper(db_path)
    db.connect()
    anotaciones_df = db.get_annotations()
    libros_ereader_df = db.get_books()
    db.close()
    print(f"✅ {len(anotaciones_df)} anotaciones y {len(libros_ereader_df)} libros cargados.")

    # --- 2. Obtención de metadatos de Dropbox con caché inteligente ---
    epub_metadata = manage_epub_metadata(
        libros_ereader_df, 
        cache_path=os.path.join("data", "epub_metadata.pkl"),
        folder_path='/Aplicaciones/Rakuten Kobo'
    )

    # --- 3. Procesamiento y enriquecimiento de datos ---
    libros_df = process_data(anotaciones_df, libros_ereader_df, epub_metadata)

    # --- 4. Sincronización con Notion ---
    print("\n🚀 Sincronizando con Notion...")
    notion = Client(auth=NOTION_API_TOKEN)

    # Crear/actualizar libros
    print("\n   -> Sincronizando libros...")
    create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID)

    # Crear nuevas anotaciones
    print("\n   -> Sincronizando anotaciones...")
    create_annotations(anotaciones_df, notion, NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID)

    # Actualizar contenido de las páginas de los libros (solo si hay cambios)
    print("\n   -> Actualizando páginas de libros...")
    create_book_pages(anotaciones_df, notion, NOTION_BOOKS_DATABASE_ID)

    print("\n✨ ¡Sincronización completada! ✨")

if __name__ == "__main__":
    main()
