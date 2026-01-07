import sqlite3
import pandas as pd
import time 

class SQLiteWrapper:
    def __init__(self, db_path):
        """
        Inicializa la conexión a la base de datos SQLite.
        
        Args:
            db_path (str): Ruta al archivo SQLite.
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establece una conexión con la base de datos."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.text_factory = lambda b: b.decode(errors='ignore')  # Ignorar errores de decodificación
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

        try:
            # Ejecutar la consulta y devolver un DataFrame
            return pd.read_sql_query(query, self.connection, params=params)
        except Exception as e:
            print(f"Error ejecutando la consulta: {e}")
            raise

    def execute_non_query(self, query, params=None):
        """
        Ejecuta una consulta SQL que no devuelve resultados (INSERT, UPDATE, DELETE).

        Args:
            query (str): Consulta SQL a ejecutar.
            params (tuple, optional): Parámetros para la consulta. Default es None.
        """
        if self.connection is None:
            raise ValueError("Conexión no establecida. Llama a `connect()` primero.")

        try:
            with self.connection as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
        except Exception as e:
            print(f"Error ejecutando la consulta no retornable: {e}")
            raise


    def get_tables_info(self):
        """
        Obtiene información sobre las tablas de la base de datos, incluyendo nombre, número de filas, número de columnas y lista de columnas.

        Returns:
            pd.DataFrame: DataFrame con la información de las tablas.
        """
        # Obtener el listado de tablas
        tables_df = self.get_query_df("SELECT name FROM sqlite_master WHERE type='table';")

        # Crear listas para almacenar la información
        table_names = []
        row_counts = []
        column_counts = []
        column_lists = []

        # Iterar sobre las tablas y recopilar información
        for table_name in tables_df['name']:
            try:
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

            except Exception as e:
                print(f"Error procesando la tabla {table_name}: {e}")

        # Crear el DataFrame con la información recopilada
        result_df = pd.DataFrame({
            "nombre": table_names,
            "num_filas": row_counts,
            "num_cols": column_counts,
            "col_names": column_lists
        })
        return result_df.sort_values("num_filas", ascending = False)

    def get_annotations(self):

        QUERY_ITEMS = """
            SELECT 
                l.Author as Autor,
                l.Title as Título, 
                COALESCE(c.Title, l.Title) as Capítulo, 
                b.ChapterProgress as `Progreso del libro`, 
                b.StartContainerPath,
                b.Text as Texto, 
                CASE 
                    WHEN b.Annotation IS NULL OR b.Annotation = '' THEN '' 
                    ELSE b.Annotation 
                END as Anotación, 
                CASE 
                    WHEN b.Type = 'highlight' THEN 'subrayado' 
                    WHEN b.Type = 'note' THEN 'nota' 
                    ELSE b.Type 
                END as Tipo,
                b.DateCreated as `Fecha de creación`
            FROM Bookmark b 
            LEFT JOIN content c ON b.ContentID = c.ContentID 
            INNER JOIN (
                SELECT DISTINCT b.VolumeID, c.Title, c.Attribution as Author
                FROM Bookmark b 
                INNER JOIN content c ON b.VolumeID = c.ContentID
            ) l ON b.VolumeID = l.VolumeID
            WHERE b.Type IN ("highlight", "note")
        """
        anotaciones_df = self.get_query_df(QUERY_ITEMS)
        anotaciones_df = anotaciones_df\
            .assign(
                fragment=lambda x: x['StartContainerPath'].str.split('#').str[1],
                point=lambda x: x['fragment'].str.extract(r'point\((.*?)\)')[0],
                point_parts=lambda x: x['point'].str.split('/').apply(lambda lst: lst if lst else [])
            )\
            .loc[lambda x: x.point.notna()]\
            .assign(
                third_point=lambda x: x['point_parts'].apply(lambda parts: parts[3] if parts else None),
                last_point=lambda x: x['point_parts'].apply(lambda parts: parts[-1] if parts else None),
            )\
        .sort_values(["Título", "Autor", "Progreso del libro", "last_point"])\
        [['Autor', 'Título', 'Capítulo', 'Progreso del libro',
            'Texto', 'Anotación', 'Tipo', 'Fecha de creación']]
        
    	# El filtro de point.notna() es para quedarnos solo con las notas de los epubs, ya que las de los kepubs son distintas
        # Si se quiere guardar las de los kepubs habría que hacer un tratamiento aparte

        return anotaciones_df

    def get_books(self):
        QUERY_BOOKS = """
            SELECT Title, Attribution, Description, ___SyncTime, DateCreated, DateLastRead, 
            NumShortcovers, ReadStatus, ___PercentRead, Language, ReadStateSynced, TimeSpentReading 
            FROM content
            WHERE ContentType = "6" AND EpubType = -1 AND ContentID LIKE 'file%'
        """

        libros_df = self.get_query_df(QUERY_BOOKS)\
            .assign(estado = lambda x: x.ReadStatus.map({0: "Sin empezar", 1: "En progreso", 2: "Leído"}))\
            .assign(tiempo_lectura = lambda x: x.TimeSpentReading.apply(lambda y: time.strftime('%H:%M:%S', time.gmtime(y))))\
            .rename(columns = {'Language': 'idioma', 'Title': 'titulo', 'Attribution': 'autor',
                            'DateLastRead': 'fecha_ultima_lectura'})\
            [['autor', 'titulo', 'idioma', 'estado', 'tiempo_lectura', 'fecha_ultima_lectura']]\
            .assign(idioma = lambda x: x.idioma.str.extract("(es|en)").fillna("en"))\
            .assign(idioma = lambda x: x.idioma.map({"es": "Español", "en": "Inglés"}))
        
        libros_df = libros_df\
            .loc[lambda x: x.estado != "Sin Comenzar"]
        return libros_df

    def close(self):
        """Cierra la conexión con la base de datos."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        else:
            print("No hay conexión activa para cerrar.")
