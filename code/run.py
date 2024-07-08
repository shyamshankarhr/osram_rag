from pathlib import Path
import os
from utils import english_downloader
from pdf_parser import PDFParser


DATA_FILE_LOCATION = './../data/datafiles/'   # path containing the data files
EN_DATA_FILE_LOCATION = './../data/datafiles_en/'  # path containing english version of the original german files
DOCUMENT_STRUCTURE_PATH = './../config/doc_titles/document_structure_en.yaml'  # file with structure of titles in the data sheets

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_LOCATION = os.path.join(script_dir, DATA_FILE_LOCATION)
EN_DATA_FILE_LOCATION = os.path.join(script_dir, EN_DATA_FILE_LOCATION)
DOCUMENT_STRUCTURE_PATH = os.path.join(script_dir, DOCUMENT_STRUCTURE_PATH)

if __name__ == '__main__':

    print('Loading OSRAM-Chatbot')

    # Download english versions if not present
    if not os.path.exists(EN_DATA_FILE_LOCATION):
          english_downloader.download_english_versions(DATA_FILE_LOCATION, EN_DATA_FILE_LOCATION)
    DATA_FILE_LOCATION = EN_DATA_FILE_LOCATION
    
    # Parse datafiles into dataframe
    pdf_parser = PDFParser(DATA_FILE_LOCATION, DOCUMENT_STRUCTURE_PATH)
    data_df = pdf_parser.get_full_dataframe()
    
    