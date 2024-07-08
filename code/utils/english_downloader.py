import os
import urllib.request
from tqdm import tqdm


def fetch_en_doc(filename, output_location, english_link_template, url_opener):
    
    product_id = filename.split('_')[1]
    en_link = english_link_template.format(product_id=product_id)
    output_file = os.path.join(output_location, filename)
    url_opener.retrieve(en_link, output_file)


def download_english_versions(input_location, output_location):

	os.makedirs(output_location, exist_ok=True)

	english_link_template = "https://www.osram.com/appsj/pdc/pdf.do?cid=GPS01_1028548&vid=PP_EUROPE_Europe_eCat&lid=EN&mpid=ZMP_{product_id}"
	url_opener = urllib.request.URLopener()

	for filename in tqdm(os.listdir(input_location), desc="Collecting data"):
		fetch_en_doc(filename, output_location, english_link_template, url_opener)
