__license__   = 'GPL v3'
__copyright__ = '2022, John Grimes <grimes.john.j@gmail.com>'
__docformat__ = 'restructuredtext en'

from importlib.metadata import metadata
import os
import re
from calibre.customize import FileTypePlugin
from calibre_plugins.ao3_tagger.PyPDF2 import PdfReader
from datetime import datetime
# from PyPDF2 import PdfReader

def big_title_index(list_of_text, title):
    for index, text in enumerate(list_of_text):
        if text == title:
            return index

def check_if_series(list_of_text):
    in_a_series = False
    for text in list_of_text:
        if text == "Series:":
            in_a_series = True
    return in_a_series

def get_pub_date(list_of_text):
    stats_list = []
    for index, text in enumerate(list_of_text):
        if text == "Stats:":
            stats_list = list_of_text[index:]
    if len(stats_list) == 0:
        return datetime(101,1,1)
    published_index = ""
    for index, text in enumerate(stats_list):
        if "Published:" in text:
            published_index = index
    if published_index == "":
        return datetime(101,1,1)
    published_date_string = stats_list[published_index][11:21]
    published_date = datetime.strptime(published_date_string, "%Y-%m-%d")
    return published_date

def get_series_data(list_of_text):
    for index, text in enumerate(list_of_text):
        if text == "Series:":
            series_name = list_of_text[index + 2]
            series_index = []
            for word in list_of_text[index + 1].split():
                if word.isdigit():
                    series_index.append(int(word))
    return [series_name, series_index[0]]

def get_tags(list_of_text):
    tags = []
    for text in list_of_text:
        if ":" in text:
            continue
        tags.append(text)
    return tags

def is_archive_pdf(text_block):
    """
    This function is checking if the PDF is from AO3.
    It searches for 'Archive of Our Own' on the first page, and if it finds it,
    returns True.
    """

    print("Checking if PDF is from 'Archive of Our Own'...")

    is_archive = False
    text_split = text_block.split("\n")

    for text in text_split:
        if re.match("Archive of Our Own", text):
            is_archive = True
            break

    if is_archive:
        print("Is an 'Archive of Our Own' PDF")
    else:
        print("Not an 'Archive of Our Own' PDF. Exiting plugin...")

    return is_archive

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

def series_index(list_of_text):
    for index, text in enumerate(list_of_text):
        if text == "Series:":
            return index



class AO3PdfTagger(FileTypePlugin):

    name                = 'AO3 PDF Tagger' # Name of the plugin
    description         = 'Set metadata for AO3 PDFs imported into Calibre'
    supported_platforms = ['windows'] # Platforms this plugin will run on
    author              = 'John Grimes' # The author of this plugin
    version             = (0, 7, 0)   # The version number of this plugin
    file_types              = set(['pdf'])
    on_import               = True
    on_postimport            = True
    minimum_calibre_version = (6, 0, 0)


    
    
    def run(self, path_to_ebook):
        from calibre.ebooks.metadata.meta import get_metadata, set_metadata
        print("Reading work...")
        page_one = read_page_one(path_to_ebook )

        if is_archive_pdf(page_one) == False:
            return

        print("Splitting text...")
        text_split = page_one.split("\n")

        title = text_split[0]
        print(f"Title is {title}")

        text_split = text_split[6:]
        title_position = big_title_index(text_split, title)
        author_position = title_position + 2
        author = text_split[author_position]
        print(f"Author is {author}")

        text_split = text_split[:title_position]
        pub_date = get_pub_date(text_split)
        print(f"Publication date is {pub_date}")

        is_series = check_if_series(text_split)
        if is_series == True:
            series_data = get_series_data(text_split)
            print(f"{title} is work {series_data[1]} in the series '{series_data[0]}")
        
        series_position = series_index(text_split)
        text_split = text_split[:series_position]

        comma_removed_text = [i for i in text_split if i != ', ' and i != ',']

        tags = get_tags(comma_removed_text)
        print(f"The tags in this story are: {tags}")


        with open(path_to_ebook, 'r+b') as file:
            ext  = os.path.splitext(path_to_ebook)[-1][1:].lower()
            mi = get_metadata(file, ext)
            mi.tags = tags
            mi.title = title
            mi.publisher = "AO3"
            mi.authors = author
            mi.pubdate = pub_date
            mi.language = "English"
            
            if is_series == True:
                mi.series = series_data[0]
                mi.series_index = series_data[1]
            
            set_metadata(file, mi, ext)
        return path_to_ebook

