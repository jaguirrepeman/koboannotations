import pandas as pd

def process_data(anotaciones_df, libros_ereader_df, epub_metadata):
    """
    Procesa y enriquece los datos de libros y anotaciones.
    """
    print("\n🔧 Procesando y enriqueciendo datos...")
    
    libros_anotaciones_df = anotaciones_df\
        [['Autor', 'Título','Fecha de creación']]\
        .assign(num_anotaciones = 1)\
        .groupby(['Autor', 'Título'])\
        .agg({"Fecha de creación": ["min", "max"], "num_anotaciones": "sum"})\
        .reset_index()\
        .set_axis(['autor', 'titulo', 'fecha_primera_nota', 'fecha_ultima_nota', 'num_anotaciones'], axis = 1)

    def clean_generos(generos):
        if isinstance(generos, list) and len(generos) == 1 and isinstance(generos[0], str):
            return generos[0].split(", ")
        return generos

    libros_dropbox = epub_metadata\
        .rename(columns = {"title": "titulo",
                           "author": "autor", "subjects": "generos", "pages": "paginas",
                           "publication_date": "fecha_publicacion"})\
        .assign(idioma = lambda x: x.language.str.extract("(es|en)").fillna("en"))\
        .assign(idioma = lambda x: x.idioma.map({"es": "Español", "en": "Inglés"}))\
        .assign(generos = lambda x: x.generos.apply(clean_generos))\
        [['autor', 'titulo', 'generos', 'paginas', 'fecha_publicacion']]

    libros_df = libros_ereader_df\
        .merge(libros_anotaciones_df, how = "left")\
        .merge(libros_dropbox, on = ["autor", "titulo"], how = "left")\
        .loc[lambda x: x.autor.notna()]\
        .assign(num_anotaciones = lambda x: x.num_anotaciones.fillna(0))
        
    print("✅ Datos procesados.")
    return libros_df
