__license__   = 'GPL v3'
__copyright__ = '2022, John Grimes <grimes.john.j@gmail.com>'
__docformat__ = 'restructuredtext en'

from importlib.metadata import metadata
import os
import re
from calibre.customize import FileTypePlugin




class AO3PdfTagger(FileTypePlugin):

    name                = 'AO3 PDF Tagger' # Name of the plugin
    description         = 'Set metadata for AO3 PDFs imported into Calibre'
    supported_platforms = ['windows'] # Platforms this plugin will run on
    author              = 'John Grimes' # The author of this plugin
    version             = (1, 0, 0)   # The version number of this plugin
    file_types              = set(['pdf'])
    on_import               = True
    on_postimport            = True
    minimum_calibre_version = (6, 0, 0)

    from calibre_plugins.ao3_tagger.PyPDF2 import PdfReader

    def read_page_one(pdf_file):
        """
        This functikon takes a PDF and reads the first page.
        The vast majority of AO3 PDFs have the relevant tags and summary info on the
        first page, so we're only extracting that much
        """

        print("Extracting PDF page one text...")
        reader = PdfReader(pdf_file)
        page_one = reader.pages[0]
        text = page_one.extract_text()
        return text

    def is_archive_pdf(file_path):
        """
        This function is checking if the PDF is from AO3.
        It searches for 'Archive of Our Own' on the first page, and if it finds it,
        returns True.
        """

        print("Checking if PDF is from 'Archive of Our Own'...")

        is_archive = False
        text = read_page_one(file_path)

        if re.match("Archive of Our Own", text):
            is_archive = True

        if is_archive:
            print("Is an 'Archive of Our Own' PDF")
        else:
            print("Not an 'Archive of Our Own' PDF. Exiting plugin...")

        return is_archive

    def construct_metadata_dictionary(file_path):
        """
        This function constructs the metadata dictionary for an AO3 PDF.

        """
        print("Constructing metadata dictionary...")

        text = read_page_one(file_path)
        fic_metadata = {}

        # After splitting, some of the text is just a period or just a comma.
        # This checks for that
        char_only_regex = "[.,]"

        # This regex checks if the text is a tag category. They always have a ':'
        tag_cat_regex = ".*:"

        text_split = text.split("\n")
        text_list_length = len(text_split)

        for index, text in enumerate(text_split):
            print("Looping through text...")
            print("Finding appropriate tags...")
            if index == 0:
                # In an AO3 PDF, the index 0 is always the title
                fic_metadata["title"] = text
                print("Acquired Title")
                previous_text = ''
            if index > 0:
                previous_text = text_split[index - 1]
            if index < (text_list_length - 1):
                next_text = text_split[index + 1]
            if index == text_list_length:
                next_text = ''
            if index == 4:
                # In an AO3 PDF, index 4 is the fic URL
                fic_metadata["url"] = text
                print("Acquired AO3 fic URL")
            if index > 5:
                if re.match("Summary", text):
                    summary_list = text_split[index + 1: len(text_split)]
                    summary_text = ' '.join(summary_list)
                    summary_text = summary_text.replace("\n", ' ')
                    summary_text = summary_text.replace("Notes", '')
                    summary_text = summary_text.replace('  ', ' ')
                    fic_metadata["summary"] = summary_text
                    print("Acquired Summary")
                    continue
                if re.match('by ', text):
                    fic_metadata["author"] = next_text
                    print("Acquired Author")
                if re.match(fic_metadata["title"], text):
                    continue
                if re.match(char_only_regex, text):
                    continue
                if re.match(tag_cat_regex, text):
                    if re.match('Chapters', text):
                        print("Acquired number of chapters")
                        chap_text = text.split('/')
                        if re.match("\?", chap_text[1]):
                            fic_metadata["chapters"] = chap_text[1]
                        else:
                            fic_metadata["chapters"] = int(chap_text[1])
                        continue
                    if re.match('Completed', text):
                        print("Acquired completed date")
                        fic_metadata["completed"] = text[11:len(text)]
                        continue
                    if re.match('Publish', text):
                        print("Acquired published date")
                        fic_metadata["published"] = text[11:len(text)]
                        continue
                    if re.match('Language', text):
                        print("Acquired language")
                        fic_metadata["language"] = next_text
                        continue
                    if re.match('Words', text):
                        print("Acquired word count")
                        fic_metadata['wordCount'] = text[7:len(text)]
                        if fic_metadata['wordCount'] == '':
                            fic_metadata['wordCount'] = next_text
                        continue
                    if re.match('Series', text):
                        print("Fic is in a series")
                        print("Acquired series name")
                        fic_metadata["series"]["seriesName"] = text_split[index + 2]
                        print("Acquired position in the series")
                        fic_metadata["series"]["part"] = int(next_text[5])
                    fic_metadata["tagCategories"].append(text[:-1])
                    continue
                if not re.match(char_only_regex, previous_text) and not re.match(tag_cat_regex, previous_text):
                    continue
                if re.match(char_only_regex, next_text) or re.match(tag_cat_regex, next_text) or next_text == '':
                    fic_metadata["tags"].append(text)
                if not re.match(char_only_regex, next_text) and not re.match(tag_cat_regex, next_text):
                    if re.match('Part', text):
                        fic_metadata["tags"].append(next_text)
                        continue
                    if re.match(fic_metadata["title"], next_text):
                        continue
                    tag = text + ' ' + next_text
                    fic_metadata["tags"].append(tag)

        return fic_metadata
    
    def run(self, path_to_ebook):
        from calibre.ebooks.metadata.meta import get_metadata, set_metadata

        if is_archive_pdf(path_to_ebook) == False:
            return
        
        metadata_dictionary = construct_metadata_dictionary(path_to_ebook)
        
        with open(path_to_ebook, 'r+b') as file:
            ext  = os.path.splitext(path_to_ebook)[-1][1:].lower()
            mi = get_metadata(file, ext)
            mi.tags = metadata_dictionary["tags"]
            mi.title = metadata_dictionary["title"]
            mi.authors = metadata_dictionary["author"]
            mi.publisher = "AO3"
            mi.pubdate = metadata_dictionary["published"]
            if metadata_dictionary["language"]:
                mi.language = metadata_dictionary["language"]
            if metadata_dictionary["summary"]:
                mi.comments = metadata_dictionary["summary"]
            if metadata_dictionary["series"]:
                mi.series = metadata_dictionary["series"]["seriesName"]
                mi.series_index = metadata_dictionary["series"]["part"]
            
            set_metadata(file, mi, ext)
        return path_to_ebook

