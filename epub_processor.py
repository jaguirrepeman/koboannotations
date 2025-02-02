import zipfile
from xml.etree import ElementTree as ET

class EpubProcessor:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.metadata = {}
        self.root = None

    def extract_opf_content(self):
        """
        Extrae el archivo 'OEBPS/content.opf' del archivo EPUB y lo procesa como XML.
        """
        with zipfile.ZipFile(self.epub_path, 'r') as epub:
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
        # Extraer metadatos clave del árbol XML
        self.metadata = {
            'title': root.findtext('.//{http://purl.org/dc/elements/1.1/}title', default=''),
            'author': root.findtext('.//{http://purl.org/dc/elements/1.1/}creator', default=''),
            'publisher': root.findtext('.//{http://purl.org/dc/elements/1.1/}publisher', default=''),
            'language': root.findtext('.//{http://purl.org/dc/elements/1.1/}language', default=''),
            'description': root.findtext('.//{http://purl.org/dc/elements/1.1/}description', default=''),
            'subjects': [elem.text for elem in root.findall('.//{http://purl.org/dc/elements/1.1/}subject')],
            'publication_date': root.findtext('.//{http://purl.org/dc/elements/1.1/}date', default=''),
        }

    def process(self):
        """
        Procesa el archivo EPUB: extrae el contenido de 'OEBPS/content.opf' y analiza los metadatos.
        """
        self.root = self.extract_opf_content()
        self.parse_opf_metadata(self.root)

    def get_metadata(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.metadata

    def get_root(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.root
