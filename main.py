#!/usr/bin/env python3
"""
Main script to process Kobo annotations and sync with Notion.

This script:
1. Loads annotations and books from the Kobo SQLite database
2. Fetches book metadata from Dropbox
3. Syncs books and annotations to Notion databases
4. Creates structured book pages with annotations
"""

import sys
import os
import pandas as pd

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import (
    NOTION_API_TOKEN, NOTION_BOOKS_DATABASE_ID, NOTION_ANNOTATIONS_DATABASE_ID,
    APP_KEY, APP_SECRET, TOKEN_FILE, SQLITE_PATH
)
from src.db_manager import SQLiteWrapper
from src.functions_dropbox import get_epub_metadata_from_dropbox
from src.functions_notion import create_books, create_annotations, create_book_pages
from notion_client import Client


def main():
    """Main function to orchestrate the entire process."""
    
    print("🚀 Starting Kobo Annotations Processing...")
    
    # 1. Load data from Kobo SQLite database
    print("\n📖 Loading data from Kobo database...")
    db_path = os.path.join("data", SQLITE_PATH)
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database file not found at {db_path}")
        print("Please ensure your Kobo database file is in the 'data' directory.")
        return
    
    db = SQLiteWrapper(db_path)
    db.connect()
    
    try:
        anotaciones_df = db.get_annotations()
        libros_ereader_df = db.get_books()
        print(f"✅ Loaded {len(anotaciones_df)} annotations and {len(libros_ereader_df)} books")
    except Exception as e:
        print(f"❌ Error loading data from database: {e}")
        return
    finally:
        db.close()
    
    # 2. Get book metadata from Dropbox
    print("\n☁️  Fetching book metadata from Dropbox...")
    try:
        epub_metadata = get_epub_metadata_from_dropbox(
            APP_KEY, APP_SECRET, TOKEN_FILE, 
            folder_path='/Aplicaciones/Rakuten Kobo'
        )
        
        # Save metadata for future use
        metadata_path = os.path.join("data", "epub_metadata.pkl")
        epub_metadata.to_pickle(metadata_path)
        print(f"✅ Fetched metadata for {len(epub_metadata)} books and saved to {metadata_path}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch from Dropbox: {e}")
        # Try to load existing metadata
        metadata_path = os.path.join("data", "epub_metadata.pkl")
        if os.path.exists(metadata_path):
            epub_metadata = pd.read_pickle(metadata_path)
            print(f"📄 Loaded existing metadata for {len(epub_metadata)} books")
        else:
            print("❌ No existing metadata found. Continuing without Dropbox data.")
            epub_metadata = pd.DataFrame()
    
    # 3. Process and merge data
    print("\n🔄 Processing and merging data...")
    
    # Process annotations count by book
    libros_anotaciones_df = (anotaciones_df
        [['Autor', 'Título', 'Fecha de creación']]
        .assign(num_anotaciones=1)
        .groupby(['Autor', 'Título'])
        .agg({"Fecha de creación": ["min", "max"], "num_anotaciones": "sum"})
        .reset_index()
        .set_axis(['autor', 'titulo', 'fecha_primera_nota', 'fecha_ultima_nota', 'num_anotaciones'], axis=1)
    )
    
    # Process Dropbox metadata if available
    if not epub_metadata.empty:
        def clean_generos(generos):
            if len(generos) == 1 and isinstance(generos[0], str):
                return generos[0].split(", ")
            return generos

        libros_dropbox = (epub_metadata
            .rename(columns={
                "title": "titulo", "author": "autor", "subjects": "generos", 
                "pages": "paginas", "publication_date": "fecha_publicacion"
            })
            .assign(idioma=lambda x: x.language.str.extract("(es|en)").fillna("en"))
            .assign(idioma=lambda x: x.idioma.map({"es": "Español", "en": "Inglés"}))
            .assign(generos=lambda x: x.generos.apply(clean_generos))
            [['autor', 'titulo', 'generos', 'paginas', 'fecha_publicacion']]
        )
    else:
        libros_dropbox = pd.DataFrame(columns=['autor', 'titulo', 'generos', 'paginas', 'fecha_publicacion'])
    
    # Merge all book data
    libros_df = (libros_ereader_df
        .merge(libros_anotaciones_df, how="left")
        .merge(libros_dropbox, on=["autor", "titulo"], how="left")
        .loc[lambda x: x.autor.notna()]
        .assign(num_anotaciones=lambda x: x.num_anotaciones.fillna(0))
    )
    
    print(f"✅ Processed data for {len(libros_df)} books")
    
    # 4. Initialize Notion client
    print("\n🔗 Connecting to Notion...")
    if not NOTION_API_TOKEN:
        print("❌ Error: NOTION_API_TOKEN not found in environment variables")
        return
    
    try:
        notion = Client(auth=NOTION_API_TOKEN)
        print("✅ Connected to Notion")
    except Exception as e:
        print(f"❌ Error connecting to Notion: {e}")
        return
    
    # 5. Create/update books in Notion (optimized)
    print("\n📚 Syncing books to Notion...")
    try:
        create_books(libros_df, notion, NOTION_BOOKS_DATABASE_ID)
    except Exception as e:
        print(f"❌ Error syncing books: {e}")
        return
    
    # 6. Create/update annotations in Notion (only new ones)
    print("\n📝 Syncing annotations to Notion...")
    try:
        create_annotations(
            anotaciones_df, notion, 
            NOTION_ANNOTATIONS_DATABASE_ID, NOTION_BOOKS_DATABASE_ID,
            delete_existing=False
        )
    except Exception as e:
        print(f"❌ Error syncing annotations: {e}")
        return
    
    # 7. Create book pages with annotations (only if content changed)
    print("\n📖 Creating book pages with annotations...")
    try:
        create_book_pages(
            anotaciones_df, notion, NOTION_BOOKS_DATABASE_ID,
            clear_content=False
        )
    except Exception as e:
        print(f"❌ Error creating book pages: {e}")
        return
    
    print("\n🎉 All done! Your Kobo annotations have been successfully synced to Notion.")


if __name__ == "__main__":
    main()