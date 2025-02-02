import zipfile
from xml.etree import ElementTree as ET
import json
import re

class EpubProcessor:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.metadata = {}

    def _extract_opf_content(self):
        """
        Extrae el archivo 'OEBPS/content.opf' del archivo EPUB y lo procesa como XML.
        """
        with zipfile.ZipFile(self.epub_path, 'r') as epub:
            opf_file = next((file for file in epub.namelist() if file.endswith('OEBPS/content.opf')), None)
            if not opf_file:
                raise FileNotFoundError("'OEBPS/content.opf' no encontrado en el archivo EPUB.")
            with epub.open(opf_file) as f:
                return ET.parse(f).getroot()
            
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

    def _get_text_from_element(self, root, tag, ns=None):
        """
        Devuelve el texto de un elemento XML, manejando el espacio de nombres si es necesario.
        """
        element = root.find(f'.//{{{ns}}}{tag}' if ns else f'.//{tag}')
        return element.text if element is not None else ''

    def _parse_metadata(self, root):
        """
        Analiza el contenido del archivo OPF (como XML) para extraer metadatos relevantes.
        """
        ns = 'http://purl.org/dc/elements/1.1/'
        self.metadata = {
            'title': self._get_text_from_element(root, 'title', ns),
            'author': self._get_text_from_element(root, 'creator', ns),
            'publisher': self._get_text_from_element(root, 'publisher', ns),
            'language': self._get_text_from_element(root, 'language', ns),
            'description': self._get_text_from_element(root, 'description', ns),
            'subjects': [elem.text for elem in root.findall(f'.//{{{ns}}}subject')],
            'publication_date': self._get_text_from_element(root, 'date', ns),
        }

    def _parse_pages_metadata(self, root):
        """
        Extrae el número de páginas desde la etiqueta <meta> correspondiente.
        """
        ns = 'http://www.idpf.org/2007/opf'
        pages_meta = root.find(f'.//{{{ns}}}meta[@name="calibre:user_metadata:#pages"]')
        if pages_meta is not None:
            try:
                content = pages_meta.attrib.get('content', '')
                parsed_content = json.loads(content.replace('&quot;', '"'))  # Sustituir entidades HTML por comillas
                self.metadata['pages'] = parsed_content.get('#value#', 0)
            except json.JSONDecodeError:
                self.metadata['pages'] = None
        else:
            self.metadata['pages'] = None

    def process(self):
        """
        Procesa el archivo EPUB: extrae el contenido de 'OEBPS/content.opf' y analiza los metadatos.
        """
        try:
            root = self._extract_opf_content()
            self._parse_metadata(root)
            self._parse_pages_metadata(root)
        except Exception as e:
            raise RuntimeError(f"Error procesando el archivo EPUB: {e}")

    def get_metadata(self):
        """
        Devuelve los metadatos extraídos del archivo OPF.
        """
        return self.metadata


# Ejemplo de uso
if __name__ == "__main__":
    epub_path = "ruta_al_archivo.epub"
    processor = EpubProcessor(epub_path)
    try:
        processor.process()
        print("Metadatos:", processor.get_metadata())
    except Exception as e:
        print(f"Error procesando el archivo EPUB: {e}")
