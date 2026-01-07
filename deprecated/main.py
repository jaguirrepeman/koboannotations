from pruebas.functions_kobo import extract_books_and_annotations
from pruebas.functions_notion import add_book_to_notion, add_annotation_to_notion, get_book_id

def main():
    # Ruta al archivo SQLite de Kobo
    sqlite_path = "KoboReader.sqlite"

    # Extraer libros y anotaciones
    books, book_annotations = extract_books_and_annotations(sqlite_path)

    # Añadir libros a Notion
    for book in books:
        print(f"Añadiendo libro: {book['title']}")
        add_book_to_notion(book["title"], book["author"])

    # Añadir anotaciones a Notion
    for book_title, annotations in book_annotations.items():
        book_id = get_book_id(book_title)
        print(f"Añadiendo anotaciones para el libro: {book_title}")
        for annotation in annotations:
            add_annotation_to_notion(
                annotation["text"],
                annotation["chapter"],
                book_id
            )

if __name__ == "__main__":
    main()
