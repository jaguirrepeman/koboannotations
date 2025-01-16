import sqlite3
import pandas as pd

class SQLiteWrapper:
    def __init__(self, db_path):
        """
        Inicializa la conexión a la base de datos SQLite.
        
        Args:
            db_path (str): Ruta al archivo SQLite.
        """
        self.db_path = db_path
        self.connection = None

    def get_tables_info(self):
        # Obtener el listado de tablas
        tables_df = self.get_query_df("SELECT name FROM sqlite_master WHERE type='table';")

        # Crear listas para almacenar la información
        table_names = []
        row_counts = []
        column_counts = []
        column_lists = []

        # Iterar sobre las tablas y recopilar información
        for table_name in tables_df['name']:
            # Contar filas en la tabla
            row_count_query = f"SELECT COUNT(*) AS row_count FROM {table_name};"
            row_count = self.get_query_df(row_count_query)['row_count'].iloc[0]
            
            # Obtener información de las columnas
            pragma_query = f"PRAGMA table_info('{table_name}');"
            columns_info = self.get_query_df(pragma_query)
            columns = columns_info['name'].tolist()
            column_count = len(columns)
            
            # Almacenar resultados
            table_names.append(table_name)
            row_counts.append(row_count)
            column_counts.append(column_count)
            column_lists.append(columns)

        # Crear el DataFrame con la información recopilada
        result_df = pd.DataFrame({
            "nombre": table_names,
            "num_filas": row_counts,
            "num_cols": column_counts,
            "col_names": column_lists
        })\
            .loc[lambda x: x.num_filas > 0]
        return result_df

    def connect(self):
        """Establece una conexión con la base de datos."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
        else:
            print("Ya existe una conexión activa.")

    def get_query_df(self, query, params=None):
        """
        Ejecuta una consulta SQL y devuelve un DataFrame.

        Args:
            query (str): Consulta SQL a ejecutar.
            params (tuple, optional): Parámetros para la consulta. Default es None.

        Returns:
            pd.DataFrame: Resultados de la consulta.
        """
        if self.connection is None:
            raise ValueError("Conexión no establecida. Llama a `connect()` primero.")
        
        # Ejecutar la consulta y devolver un DataFrame
        return pd.read_sql_query(query, self.connection, params=params)

    def execute_non_query(self, query, params=None):
        """
        Ejecuta una consulta SQL que no devuelve resultados (INSERT, UPDATE, DELETE).

        Args:
            query (str): Consulta SQL a ejecutar.
            params (tuple, optional): Parámetros para la consulta. Default es None.
        """
        if self.connection is None:
            raise ValueError("Conexión no establecida. Llama a `connect()` primero.")

        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        else:
            print("No hay conexión activa para cerrar.")
