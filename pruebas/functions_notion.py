from notion_client import Client
from config import NOTION_API_TOKEN, NOTION_BOOKS_DATABASE_ID, NOTION_ANNOTATIONS_DATABASE_ID

# Inicializar cliente de Notion
notion = Client(auth=NOTION_API_TOKEN)

def add_book_to_notion(title, author, genre=None):
    """
    Añade un libro a la base de datos de libros en Notion.
    """
    notion.pages.create(
        parent={"database_id": NOTION_BOOKS_DATABASE_ID},
        properties={
            "Título": {"title": [{"text": {"content": title}}]},
            "Autor": {"rich_text": [{"text": {"content": author}}]},
            "Género": {"rich_text": [{"text": {"content": genre}}]} if genre else None,
        },
    )

def get_book_id(title):
    """
    Obtiene el ID de un libro en la base de datos de Notion por su título.
    """
    books = notion.databases.query(
        database_id=NOTION_BOOKS_DATABASE_ID,
        filter={"property": "Título", "title": {"equals": title}}
    )
    if books["results"]:
        return books["results"][0]["id"]
    raise ValueError(f"El libro '{title}' no existe en la base de datos.")

def add_annotation_to_notion(text, chapter, book_id):
    """
    Añade una anotación vinculada a un libro en la base de datos de anotaciones.
    """
    notion.pages.create(
        parent={"database_id": NOTION_ANNOTATIONS_DATABASE_ID},
        properties={
            "Texto": {"rich_text": [{"text": {"content": text}}]},
            "Capítulo": {"number": chapter},
            "Libros": {"relation": [{"id": book_id}]},
        },
    )
