from db_manager import SQLiteWrapper

def extract_books_and_annotations(db_path):
    """
    Extrae libros y anotaciones de la base de datos SQLite.

    Args:
        db_path (str): Ruta a la base de datos SQLite.

    Returns:
        tuple: Dos DataFrames, uno con los libros y otro con las anotaciones.
    """
    db = SQLiteWrapper(db_path)
    db.connect()

    # Consultar libros
    books_query = """
        SELECT VolumeID AS id, Title AS title, Attribution AS author
        FROM content
        WHERE Title IS NOT NULL;
        """
    books_df = db.get_query_df(books_query)

    # Consultar anotaciones
    annotations_query = """
        SELECT VolumeID AS volume_id, Text AS text, DateCreated AS date
        FROM Bookmark
        WHERE Text IS NOT NULL AND Text != '';
        """
    annotations_df = db.get_query_df(annotations_query)

    db.close()
    return books_df, annotations_df
