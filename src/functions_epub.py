import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
import json
import re
from bs4 import BeautifulSoup
import math
import pandas as pd
from datetime import datetime

def parse_dates(date_str):
    try:
        # Intentar convertir con pandas (rápido para fechas modernas)
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except (pd.errors.OutOfBoundsDatetime, ValueError):
        # Usar datetime para fechas fuera del rango
        try:
            date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
            return date.strftime('%Y-%m-%d')
        except ValueError:
            # Manejo de errores si el formato es inválido
            return None

class EpubProcessor:
    def __init__(self, epub_content=None, epub_path=None):
        """
        Se inicializa con el contenido del archivo EPUB en memoria o con la ruta del archivo.
        """
        self.epub_path = epub_path
        self.epub_content = epub_content
        self.metadata = {}

    def find_opf_path(self, epub):
        """
        Encuentra la ruta al archivo OPF a través de 'META-INF/container.xml'.
        """
        try:
            with epub.open('META-INF/container.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                opf_path = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').attrib['full-path']
                return opf_path
        except Exception:
            raise FileNotFoundError("No se pudo encontrar 'META-INF/container.xml' o no contiene información válida.")

    def extract_opf_content(self):
        """
        Extrae el archivo OPF del archivo EPUB y lo procesa como XML.
        """
        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()

        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            try:
                opf_path = self.find_opf_path(epub)
            except FileNotFoundError:
                opf_path = next((file for file in epub.namelist() if file.endswith('.opf')), None)
                if not opf_path:
                    raise FileNotFoundError("No se encontró ningún archivo OPF en el EPUB.")

            with epub.open(opf_path) as f:
                tree = ET.parse(f)
                return tree.getroot()

    def parse_opf_metadata(self, root):
        """
        Analiza el contenido del archivo OPF (como XML) para extraer metadatos relevantes.
        """
        ns = {'opf': 'http://www.idpf.org/2007/opf'}  # Namespace OPF

        self.metadata = {
            'title': root.findtext('.//{http://purl.org/dc/elements/1.1/}title', default=''),
            'author': root.findtext('.//{http://purl.org/dc/elements/1.1/}creator', default=''),
            'publisher': root.findtext('.//{http://purl.org/dc/elements/1.1/}publisher', default=''),
            'language': root.findtext('.//{http://purl.org/dc/elements/1.1/}language', default=''),
            'description': root.findtext('.//{http://purl.org/dc/elements/1.1/}description', default=''),
            'subjects': [elem.text for elem in root.findall('.//{http://purl.org/dc/elements/1.1/}subject')],
            'publication_date': root.findtext('.//{http://purl.org/dc/elements/1.1/}date', default=''),
            'pages_calc_pr': self.calculate_precise_page_count(chars_per_page=1300),
            'pages_calc': self.calculate_precise_page_count(chars_per_page=1024)
        }
        self.metadata['publication_date'] = parse_dates(self.metadata['publication_date'])

    def parse_pages_metadata(self, root):
        """
        Extrae el número de páginas desde la etiqueta <meta> correspondiente.
																								
        """
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        pages_meta = root.find('.//opf:meta[@name="calibre:user_metadata:#pages"]', namespaces=ns)
        
        if pages_meta is not None:
            try:
                content = pages_meta.attrib.get('content', '')
                parsed_content = json.loads(content.replace('&quot;', '"'))
                pages = parsed_content.get('#value#', 0)
                self.metadata['pages'] = pages
            except json.JSONDecodeError:
                self.metadata['pages'] = None
        else:
            self.metadata['pages'] = None


    def calculate_precise_page_count(self, chars_per_page=1300, calculo_pags="cap",
                                     debug = False):
        from bs4 import BeautifulSoup  # Para analizar HTML

        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()
        total_chars = 0
        total_paginas = 0
        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            # Obtener el orden de los capítulos según el ToC
            toc_files = self.get_toc_order(epub)
            available_files = epub.namelist()  # Lista de archivos disponibles en el EPUB
            toc_files = [f"OEBPS/{t}" for t in toc_files]

            for file_name in toc_files:
                if file_name in available_files:
                    with epub.open(file_name) as f:
                        file_content = f.read().decode('utf-8')
                        soup = BeautifulSoup(file_content, 'html.parser')
                        text = soup.get_text()  # Extrae solo el texto visible
                        if calculo_pags == "total":
                            total_chars += len(text)
                        else:
                            pags_cap = max(len(text) // chars_per_page, 1)
                            total_paginas += pags_cap
                            if ("articulo" not in file_name) and debug: 
                                print(file_name, total_paginas, pags_cap, len(text))
                else:
                    print(f"{self.metadata['title']}, {self.metadata['author']}: Archivo '{file_name}' no encontrado en el EPUB.")
            if calculo_pags == "total":
                total_paginas = max(total_chars // chars_per_page, 1)
            else: 
                total_paginas += 1
        return total_paginas



    def get_spine_files(self):
        root = self.extract_opf_content()
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        spine_ids = [item.attrib['idref'] for item in root.findall('.//opf:spine/opf:itemref', namespaces=ns)]

        manifest = {item.attrib['id']: item.attrib['href'] for item in root.findall('.//opf:manifest/opf:item', namespaces=ns)}
        spine_files = [manifest[idref] for idref in spine_ids if idref in manifest]

        # Ajusta las rutas relativas basándote en la ubicación del OPF
        opf_path = self.find_opf_path(zipfile.ZipFile(BytesIO(self.epub_content)))
        opf_folder = '/'.join(opf_path.split('/')[:-1])
        return [f"{opf_folder}/{file}" for file in spine_files]

    def get_toc_order(self, epub):
        """
        Extrae el orden de los capítulos desde el archivo toc.ncx.
        """
        try:
            toc_path = next((file for file in epub.namelist() if file.endswith('toc.ncx')), None)
            if not toc_path:
                raise FileNotFoundError("No se encontró ningún archivo toc.ncx en el EPUB.")

            with epub.open(toc_path) as f:
                soup = BeautifulSoup(f.read(), 'xml')
                nav_points = soup.find_all('navPoint')
                ordered_files = [nav_point.content['src'].split('#')[0] for nav_point in nav_points if nav_point.content]
                return list(dict.fromkeys(ordered_files))  # Eliminar duplicados conservando el orden
        except Exception as e:
            print(f"Error al procesar el archivo toc.ncx: {e}")
            return self.get_spine_files()

    def process(self):
        """
        Procesa el archivo EPUB: extrae el contenido del OPF y analiza los metadatos.
        """
        root = self.extract_opf_content()
        self.parse_opf_metadata(root)
        self.parse_pages_metadata(root)

    def get_metadata(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.metadata

    def get_content(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.epub_content

    def get_file(self, file_name, format = "processed"):
        with zipfile.ZipFile(BytesIO(self.epub_content), 'r') as epub:
            with epub.open(file_name) as f:
                file_content = f.read().decode('utf-8')
                if format == "processed":
                    soup = BeautifulSoup(file_content, 'html.parser')
                    file_content = soup.get_text()  # Extrae solo el texto visible
                
                return file_content