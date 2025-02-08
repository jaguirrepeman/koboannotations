import time
import requests
import dropbox
import json
import os
import pandas as pd
from functions_epub_pruebas import EpubProcessor_pruebas

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
def get_epub_metadata_from_dropbox(APP_KEY, APP_SECRET, TOKEN_FILE, 
                                   folder_path='/Aplicaciones/Rakuten Kobo'):
    ACCESS_TOKEN = get_access_token(APP_KEY, APP_SECRET, TOKEN_FILE)
    all_metadata = []
    try:
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        response = dbx.files_list_folder(path=folder_path)

        for entry in response.entries:
            if entry.name.endswith('.epub'):
                try:
                    # print(f"Procesando archivo: {entry.name}")

                    # Descargar el archivo .epub directamente en memoria
                    metadata, res = dbx.files_download(path=f"{folder_path}/{entry.name}")
                    epub_content = res.content  # Asegúrate de obtener los bytes del contenido

                    # Usar la clase EpubProcessor para procesar el archivo directamente desde la memoria
                    processor = EpubProcessor_pruebas(epub_content=epub_content)
                    processor.process()

                    # Obtener los metadatos del archivo EPUB
                    metadata = processor.get_metadata()
                    metadata['filename'] = entry.name  # Agregar el nombre del archivo como columna
                    metadata['processor'] = processor  # Agregar el nombre del archivo como columna

                    # Agregar los metadatos a la lista
                    all_metadata.append(metadata)
                except Exception as e:
                    print(f"Fallo en {entry.name}")
                    print(e)

        df = pd.DataFrame(all_metadata)
        return df
    except Exception as e:
        print(f"Error: {e}")


