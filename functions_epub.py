import dropbox
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
import json

class EpubProcessor:
    def __init__(self, epub_content=None, epub_path=None):
        """
        Se inicializa con el contenido del archivo EPUB en memoria o con la ruta del archivo.
        """
        self.epub_path = epub_path
        self.epub_content = epub_content
        self.metadata = {}

    def extract_opf_content(self):
        """
        Extrae el archivo 'OEBPS/content.opf' del archivo EPUB y lo procesa como XML.
        """
        content = self.epub_content if self.epub_content else open(self.epub_path, 'rb').read()

        with zipfile.ZipFile(BytesIO(content), 'r') as epub:
            opf_file = next((file for file in epub.namelist() if file.endswith('OEBPS/content.opf')), None)
            if not opf_file:
                raise FileNotFoundError("'OEBPS/content.opf' no encontrado en el archivo EPUB.")

            # Leer y parsear el contenido como XML directamente
            with epub.open(opf_file) as f:
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

    def process(self):
        """
        Procesa el archivo EPUB: extrae el contenido de 'OEBPS/content.opf' y analiza los metadatos.
        """
        root = self.extract_opf_content()
        self.parse_opf_metadata(root)
        self.parse_pages_metadata(root)

    def get_metadata(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.metadata

# Función para calcular el número de páginas (ajústala según el método que estés utilizando)
def calculate_pages_kobo_style(epub_content):
    # Aquí deberías integrar la lógica que calcula las páginas de estilo Kobo a partir del contenido EPUB
    return 100  # Este es solo un valor de ejemplo
