import time
import requests
import dropbox
import json
import os
import pandas as pd
from src.functions_epub import EpubProcessor
from src.config import APP_KEY, APP_SECRET, TOKEN_FILE

def authenticate(APP_KEY, APP_SECRET, TOKEN_FILE):
    """Autentica al usuario la primera vez y guarda el token."""
    print("Autenticación inicial necesaria. Sigue las instrucciones.")
    auth_url = (
        f"https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline"
    )
    print(f"Ve a este enlace para autorizar la aplicación: {auth_url}")
    auth_code = input("Introduce el código de autorización: ").strip()

    # Intercambiar el código por un token de acceso y refresco
    response = requests.post(
        "https://api.dropbox.com/oauth2/token",
        data={
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": APP_KEY,
            "client_secret": APP_SECRET,
        },
    )

    if response.status_code == 200:
        tokens = response.json()
        tokens["expires_at"] = time.time() + tokens.get("expires_in", 0)
        print("Tokens recibidos:", tokens)  # Depuración
        save_tokens(tokens, TOKEN_FILE)
        print("Autenticación exitosa. Los tokens se han guardado.")
    else:
        raise Exception("Error al autenticar: ", response.json())

def save_tokens(tokens, TOKEN_FILE):
    """Guarda los tokens en un archivo."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens(TOKEN_FILE):
    """Carga los tokens desde el archivo."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    else:
        return None

def refresh_token(APP_KEY, APP_SECRET, TOKEN_FILE):
    """Renueva el token de acceso si ha expirado."""
    tokens = load_tokens(TOKEN_FILE)
    if not tokens:
        raise Exception("No hay tokens almacenados. Por favor, autentícate primero.")

    if tokens["expires_at"] > time.time():
        # El token aún es válido
        return tokens["access_token"]

    # El token ha expirado, renueva usando el refresh_token
    response = requests.post(
        "https://api.dropbox.com/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": APP_KEY,
            "client_secret": APP_SECRET,
        },
    )

    if response.status_code == 200:
        new_tokens = response.json()
        new_tokens["refresh_token"] = tokens["refresh_token"]  # Mantener el refresh_token existente
        new_tokens["expires_at"] = time.time() + new_tokens["expires_in"]
        save_tokens(new_tokens, TOKEN_FILE)
        return new_tokens["access_token"]
    else:
        raise Exception("Error al renovar el token: ", response.json())

def get_access_token(APP_KEY, APP_SECRET, TOKEN_FILE):
    """Obtiene un token de acceso válido, renovándolo si es necesario."""
    tokens = load_tokens(TOKEN_FILE)
    if not tokens:
        print("No se encontraron tokens. Autenticando por primera vez...")
        authenticate(APP_KEY, APP_SECRET, TOKEN_FILE)
        tokens = load_tokens(TOKEN_FILE)
    return refresh_token(APP_KEY, APP_SECRET, TOKEN_FILE)

# Función para obtener metadatos desde Dropbox
def get_epub_metadata_from_dropbox(folder_path='/Aplicaciones/Rakuten Kobo', books_df_to_process=None):
    ACCESS_TOKEN = get_access_token(APP_KEY, APP_SECRET, TOKEN_FILE)
    all_metadata = []
    try:
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        response = dbx.files_list_folder(path=folder_path)

        # Crear un conjunto de títulos de libros a procesar para una búsqueda más rápida
        if books_df_to_process is not None:
            titles_to_process = set(books_df_to_process['titulo'])
        else:
            titles_to_process = None

        for entry in response.entries:
            if entry.name.endswith('.epub'):
                # Extraer el título del nombre del archivo para comparar
                file_title = os.path.splitext(entry.name)[0]

                # Si se especifica una lista de libros, procesar solo esos
                if titles_to_process and file_title not in titles_to_process:
                    continue

                try:
                    # Descargar el archivo .epub directamente en memoria
                    metadata, res = dbx.files_download(path=f"{folder_path}/{entry.name}")
                    epub_content = res.content

                    # Usar la clase EpubProcessor para procesar el archivo
                    processor = EpubProcessor(epub_content=epub_content)
                    processor.process()

                    # Obtener los metadatos
                    metadata = processor.get_metadata()
                    metadata['filename'] = entry.name
                    all_metadata.append(metadata)
                except Exception as e:
                    print(f"Fallo en {entry.name}: {e}")

        df = pd.DataFrame(all_metadata)
        return df
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()
        
def calculate_pages_kobo_style(epub_content, chars_per_page=1024):
    """DEPRECATED"""
    # Extraer contenido del .epub (contenido en formato zip)
    text = ""
    with zipfile.ZipFile(epub_content) as epub:
        for file in epub.namelist():
            if file.endswith('.html') or file.endswith('.xhtml'):
                with epub.open(file) as f:
                    content = f.read().decode('utf-8')
                    # Eliminar etiquetas HTML y quedarnos con el texto
                    text += re.sub(r'<[^>]+>', '', content)
    
    # Calcular el número de páginas basado en caracteres
    num_pages = len(text) // chars_per_page
    return num_pages

def manage_epub_metadata(libros_ereader_df, cache_path="data/epub_metadata.pkl", folder_path='/Aplicaciones/Rakuten Kobo'):
    """
    Gestiona la caché de metadatos de epub desde Dropbox.
    Solo descarga metadatos de libros nuevos que no estén en la caché.
    
    Args:
        libros_ereader_df: DataFrame con los libros del E-Reader (columnas: 'titulo', 'autor')
        cache_path: Ruta al archivo de caché
        folder_path: Ruta a la carpeta de Dropbox
        
    Returns:
        DataFrame con los metadatos de todos los libros (columnas: 'title', 'author', etc.)
    """
    print("\n🔄 Obteniendo metadatos de Dropbox...")
    
    # Cargar caché si existe
    if os.path.exists(cache_path):
        print("   -> Usando caché de metadatos.")
        epub_metadata = pd.read_pickle(cache_path)
    else:
        print("   -> No se encontró caché inicial.")
        epub_metadata = pd.DataFrame()

    # Identificar libros nuevos que no están en la caché
    if not epub_metadata.empty and 'title' in epub_metadata.columns:
        # Los metadatos de Dropbox usan 'title', los del E-Reader usan 'titulo'
        libros_en_cache = set(epub_metadata['title'].dropna().unique())
        libros_nuevos_df = libros_ereader_df[~libros_ereader_df['titulo'].isin(libros_en_cache)]
    else:
        # Si la caché está vacía o no tiene la columna correcta, procesar todos
        libros_nuevos_df = libros_ereader_df

    # Si hay libros nuevos, obtener sus metadatos y actualizar la caché
    if not libros_nuevos_df.empty:
        print(f"   -> {len(libros_nuevos_df)} libros nuevos detectados. Obteniendo sus metadatos de Dropbox...")
        nuevos_metadatos = get_epub_metadata_from_dropbox(
            folder_path=folder_path, 
            books_df_to_process=libros_nuevos_df
        )
        
        if not nuevos_metadatos.empty:
            epub_metadata = pd.concat([epub_metadata, nuevos_metadatos], ignore_index=True)
            epub_metadata.to_pickle(cache_path)
            print("   -> Caché de metadatos actualizada.")
        else:
            print("   -> No se pudieron obtener metadatos para los libros nuevos.")
    else:
        print("   -> No hay libros nuevos que procesar desde Dropbox.")
    
    return epub_metadata

def refresh_access_token(refresh_token, app_key, app_secret):
    url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    auth = (app_key, app_secret)
    response = requests.post(url, data=data, auth=auth)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Error al refrescar el token: {response.content}")

    # Ejemplo de uso:
    # APP_KEY = "sxz8wblgpfgjii1"
    # APP_SECRET = "i4zsuphuk1s2zxu"
    # REFRESH_TOKEN = "your_refresh_token"

    # new_access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
    # print(f"Nuevo token de acceso: {new_access_token}")

