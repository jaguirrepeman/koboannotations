import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
import json
import re

class EpubProcessor_pruebas:
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
            # Intentar encontrar la ruta al OPF desde el archivo container.xml
            try:
                opf_path = self.find_opf_path(epub)
            except FileNotFoundError:
                # Si no existe container.xml, buscar cualquier archivo .opf como fallback
                opf_path = next((file for file in epub.namelist() if file.endswith('.opf')), None)
                if not opf_path:
                    raise FileNotFoundError("No se encontró ningún archivo OPF en el EPUB.")

            # Leer y parsear el contenido como XML directamente
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
        }

    def parse_pages_metadata(self, root):
        """
        Extrae el número de páginas desde la etiqueta <meta> correspondiente.
        """
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        pages_meta = root.find('.//opf:meta[@name="calibre:user_metadata:#pages"]', namespaces=ns)
        
        if pages_meta is not None:
            try:
                content = pages_meta.attrib.get('content', '')
                parsed_content = json.loads(content.replace('&quot;', '"'))  # Sustituir entidades HTML por comillas
                pages = parsed_content.get('#value#', 0)  # Extraer el valor de '#value#'
                self.metadata['pages'] = pages
            except json.JSONDecodeError:
                self.metadata['pages'] = None
        else:
            self.metadata['pages'] = None

    def list_files(self):
        """
        Lista todos los archivos dentro del EPUB.
        """
        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()

        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            return epub.namelist()

    def read_file_content(self, file_name):
        """
        Lee el contenido de un archivo específico dentro del EPUB.
        """
        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()

        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            if file_name in epub.namelist():
                with epub.open(file_name) as f:
                    return f.read().decode('utf-8')  # Decodificar como texto UTF-8
            else:
                raise FileNotFoundError(f"El archivo '{file_name}' no se encuentra en el EPUB.")


    def get_epub_page_count(self, chars_per_page=1024):
        """
        Calcula una aproximación del número de páginas en un archivo EPUB.
        
        Args:
            epub_content (bytes): Contenido del archivo EPUB (si está en memoria).
            epub_path (str): Ruta al archivo EPUB (si está en disco).
            chars_per_page (int): Número de caracteres por página para el cálculo.
        
        Returns:
            int: Número aproximado de páginas.
        """
        # Leer el contenido del EPUB desde memoria o desde el archivo
        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()

        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            # Filtrar los archivos XHTML/HTML dentro del EPUB
            text_files = [f for f in epub.namelist() if f.endswith(('.xhtml', '.html'))]
            total_chars = 0

            for file_name in text_files:
                with epub.open(file_name) as f:
                    file_content = f.read().decode('utf-8')
                    # Eliminar etiquetas HTML para contar solo caracteres visibles
                    text = re.sub(r'<[^>]+>', '', file_content)
                    total_chars += len(text)

        # Calcular el número de páginas basándose en los caracteres totales
        page_count = total_chars // chars_per_page
        return max(page_count, 1)  # Asegurar al menos una página

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

