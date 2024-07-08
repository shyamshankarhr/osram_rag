from pathlib import Path
import os
from utils import english_downloader


DATA_FILE_LOCATION = './../data/datafiles/'   # path containing the data files
EN_DATA_FILE_LOCATION = './../data/datafiles_en/'  # path containing english version of the original german files

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_LOCATION = os.path.join(script_dir, DATA_FILE_LOCATION)
EN_DATA_FILE_LOCATION = os.path.join(script_dir, EN_DATA_FILE_LOCATION)


if __name__ == '__main__':
    print('Hello World!')

    # Download english versions if not present
    if not os.path.exists(EN_DATA_FILE_LOCATION):
          english_downloader.download_english_versions(DATA_FILE_LOCATION, EN_DATA_FILE_LOCATION)
    
    