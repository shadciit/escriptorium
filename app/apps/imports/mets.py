import logging
import zipfile
from collections import namedtuple
from parser import ParserError

from PIL import Image

logger = logging.getLogger(__name__)

METSPage = namedtuple('METSPage', ['image', 'sources'], defaults=[None, {}])


class METSProcessor:

    def __init__(self, mets_xml, archive=None):
        self.mets_xml = mets_xml
        self.archive = archive

    def retrieve_in_archive(self, filename):
        with zipfile.ZipFile(self.archive) as archive:
            return archive.open(filename)

    def get_files_from_file_sec(self):
        file_sec = self.mets_xml.find("fileSec", self.mets_xml.nsmap)
        if not file_sec:
            raise ParserError("The file section <fileSec/> wasn't found in the METS file.")

        files = {}
        for element in file_sec.findall(".//file[@ID]", self.mets_xml.nsmap):
            files[element.get("ID")] = element

        return files

    def get_pages_from_struct_map(self):
        struct_map = self.mets_xml.find("structMap", self.mets_xml.nsmap)
        if not struct_map:
            raise ParserError("The structure mapping <structMap/> wasn't found in the METS file.")

        pages = []
        for element in struct_map.findall(".//div[@TYPE]", self.mets_xml.nsmap):
            if "page" in element.get("TYPE", ""):
                pages.append(element)

        return pages

    def get_file_pointers(self, page):
        file_pointers = []

        for element in page.findall("fptr", self.mets_xml.nsmap):
            file_pointers.append(element)

        return file_pointers

    def get_file_location(self, file):
        location = file.find("FLocat", self.mets_xml.nsmap)
        for attrib, value in location.attrib.items():
            if "href" in attrib:
                return value

        return ""

    def get_file_group_name(self, file):
        parent = file.getparent()
        if parent and "filegrp" in parent.tag.lower():
            return parent.get("USE")

        return None

    def process(self):
        mets_pages = []
        files = self.get_files_from_file_sec()

        pages = self.get_pages_from_struct_map()
        for page in pages:
            mets_page_image = None
            mets_page_sources = {}
            layers_count = 1

            file_pointers = self.get_file_pointers(page)
            for file_pointer in file_pointers:
                file = files[file_pointer.get("FILEID")]
                href = self.get_file_location(file)
                layer_name = self.get_file_group_name(file) or f"Layer {layers_count}"

                if self.archive:
                    try:
                        file = self.retrieve_in_archive(href)
                    except KeyError as e:
                        logger.error(f"File not found in the provided archive: {e}")
                        continue
                else:
                    # Retrieve the file from a distant source
                    raise NotImplementedError

                try:
                    # Testing if the retrieved file is an image
                    Image.open(file)
                    # We only want to save the first provided image
                    if not mets_page_image:
                        mets_page_image = href
                except IOError:
                    # If it's not an image then we can add it as a data source to be loaded
                    mets_page_sources[layer_name] = href
                    layers_count += 1
                finally:
                    file.close()

            mets_pages.append(METSPage(image=mets_page_image, sources=mets_page_sources))

        return mets_pages
