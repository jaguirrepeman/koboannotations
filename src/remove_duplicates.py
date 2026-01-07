"""
Script standalone para detectar y eliminar libros duplicados en Notion.
Este script es un wrapper que usa la función del módulo notion_cleanup.
"""
import os
from notion_client import Client
from src.config import NOTION_API_TOKEN, NOTION_BOOKS_DATABASE_ID
from src.notion_cleanup import remove_duplicate_books as remove_duplicates_func


def remove_duplicate_books():
    """
    Detecta y elimina libros duplicados en la base de datos de Notion.
    Mantiene solo la primera ocurrencia de cada libro.
    """
    notion = Client(auth=NOTION_API_TOKEN)
    remove_duplicates_func(notion, NOTION_BOOKS_DATABASE_ID)


if __name__ == "__main__":
    remove_duplicate_books()

