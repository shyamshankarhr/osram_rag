from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
import pandas as pd
from utils import yaml_reader
import yaml
import os
import re

class PDFParser:

    def __init__(self, file_location, doc_structure_location):

        self.file_location = file_location
        self.doc_structure_location = doc_structure_location
        self.data_file_list = os.listdir(self.file_location)
        self.tech_titles_dict = yaml_reader.read(self.doc_structure_location)


    @staticmethod
    def fetch_product_lines(title, page):  # fetches the details below the given title

        details_pattern = re.compile(r'%s\n((?:_[^\n]*\n)+)' %title)  # After \n: (...) ...: multiple items of the form _[char not \n]\n. Need not capture each item individually, so keep it as non-capturing group with ?:
        details_match = details_pattern.search(page)
        details = details_match.group(1) if details_match else ''
        details = ', '.join([i.lstrip('_') for i in details.split('\n') if len(i)>0])
        return details
    

    @staticmethod
    def clean_tech_pages(tech_pages, tech_titles_dict):

        all_titles = yaml_reader.get_all_titles(tech_titles_dict, [])
        whitespace_pattern = re.compile(r'\s+\n')
        footnotes_pattern = re.compile(r'\s*\d\).*?(?=\n|$)')
        newline_pattern = re.compile(r'\n(?!(' + '|'.join(re.escape(title) for title in all_titles) + r'))')
        country_specific_pattern = re.compile(r'( Country specific information(?:.|\n)*)')

        tech_pages = whitespace_pattern.sub('\n', tech_pages)
        tech_pages = footnotes_pattern.sub('', tech_pages)
        tech_pages = newline_pattern.sub(' ', tech_pages).strip()+'\n'
        tech_pages = tech_pages.replace(' Information according Art. 33 of EU Regulation (EC) 1907/2006 (REACh)','')
        tech_pages = country_specific_pattern.sub('\n', tech_pages)
    
        return tech_pages


    @staticmethod
    def get_country_specific_data(page):
    
        country_specific_dict = {}
        country_section_pattern = 'Country specific information\n(.+)\n(.+)\n' # 2nd line after the title is the data row
        country_section_elements = re.compile(country_section_pattern)
        country_section_matches = country_section_elements.search(page)
        
        if country_section_matches:
            country_specific_dict = {}
            country_info = country_section_matches.group(2)
            country_specific_dict = {
                # 'product_code': country_info.split()[0],  # always found in logistics section
                'METEL_code': country_info.split()[1],
                'SEG_No': country_info.split()[2],
                'STK_Number': country_info.split()[3],
                'UK_org': country_info.split()[4],
            }
        return country_specific_dict
    

    def get_product_data(self, pages):
    
        page = pages[0].page_content  # Here we only extract the main product description from first page
        product_data_dict = {}
        product_name_pattern = re.compile(r'(XBO.+)\n(XBO.+)\n') # Assumption: Product Description is written below the Product name
        product_name_match = product_name_pattern.search(page)
        product_name, product_description = product_name_match.group(1),product_name_match.group(2)
        product_data_dict['product_name'] = product_name
        product_data_dict['product_description'] = product_description
        product_data_dict['application_areas'] = self.fetch_product_lines('Areas of application', page)
        product_data_dict['product_family_benefits'] = self.fetch_product_lines('Product family benefits', page)
        product_data_dict['product_family_features'] = self.fetch_product_lines('Product family features', page)

        return product_data_dict
    

    def get_technical_data(self, pages, tech_titles_dict):

        tech_data_key = 'technical_data'  # as specified in the yaml file
        tech_data_titles = dict(zip(tech_titles_dict[tech_data_key]['parts'].keys(), [tech_titles_dict[tech_data_key]['parts'][i]['title'] for i in tech_titles_dict[tech_data_key]['parts']]))
        
        # Collecting pages with technical data
        page_2 = pages[1].page_content.split('__')[0].replace('Product datasheet','')  # Using '__' as the identifier for footnotes
        page_3 = pages[2].page_content.split('__')[0].replace('Product datasheet','')  # Using '__' as the identifier for footnotes
        tech_pages = '\n'.join([page_2, page_3])
        
        # Cleaning the technical data pages
        tech_pages = self.clean_tech_pages(tech_pages, tech_titles_dict)
        
        # Gathering elements of technical data
        tech_data_pattern = '\n((?:.*\n)+)'.join(tech_data_titles.values())+'\n((?:.*\n)+)'
        tech_data_elements = re.compile(tech_data_pattern)
        tech_matches = tech_data_elements.search(tech_pages)
            
        # Collecting the details from all the sections
        
        tech_data_dict = {}  # will store all the extracted values

        for idx, part in enumerate(tech_titles_dict[tech_data_key]['parts']):
            part_text = tech_matches.group(idx+1)
            part_titles = tech_titles_dict[tech_data_key]['parts'][part]['parts']
            found_titles = [i for i in part_titles.values() if i.replace('\\','') in part_text]  # will use only the found titles in the regex pattern
            found_keys = [{v: k for k, v in part_titles.items()}[i] for i in found_titles]  # inverting the mapping to get the keys of found titles
            part_pattern = '\s(.+)\n'.join(found_titles)+'\s(.+)\n'
            part_elements = re.compile(part_pattern)
            part_matches = part_elements.search(part_text)
            part_dict = dict(zip(found_keys,[part_matches.group(i+1) if part_matches else '' for i in range(len(found_titles))]))
            tech_data_dict[part] = part_dict
            
        # Collecting country specific information (if any)
        country_specific_dict = self.get_country_specific_data(page_3)
        
        tech_data_dict = dict(**tech_data_dict, **country_specific_dict)
            
        return tech_data_dict
    

    def get_logistics_data(self, pages):
    
        logistics_page = pages[3].page_content.split('__')[0].replace('Product datasheet','')
        logistics_dict = {}
        
        logistics_section_pattern = re.compile(r'Product code Product description Packaging unit\n\(Pieces/Unit\)Dimensions \(length\nx width x height\)Volume Gross weight\n((?:.|\n)*)')
        logistics_section_matches = logistics_section_pattern.search(logistics_page)
        logistics_info = logistics_section_matches.group(1)

        product_name = self.get_product_data(pages)['product_name']  # getting product name to match in the values' rows
        product_code = logistics_info.split(' ')[0]  # row of values start with product code
        
        product_name_pattern = r'\b' + r'\s*'.join(map(re.escape, product_name.split()))  # product name, but could have a newline character in between
        packaging_unit_pattern = '(.+\n\d)'  # assumed pattern: ends with newline followed by a digit
        dimensions_pattern = '(\d+ mm x \d+ mm x\n\d+ mm)' # Pattern: '(590 mm x 234 mm x\n234 mm)'
        volume_pattern = '(.+ dm³)'  # number followed by 'dm³''
        gross_weight_pattern = '(.+ g)'  # number followed by 'g'
        packaging_notification = '()'

        # Combining all the fields to form the pattern to parse the row of details
        logistics_pattern = re.compile(product_name_pattern+packaging_unit_pattern+dimensions_pattern+volume_pattern+gross_weight_pattern)
        logistics_matches = logistics_pattern.search(logistics_info)

        logistics_dict = {  # Using only the first row (though there are some files with multiple product codes)

                'product_code': product_code,
                'packaging_unit': logistics_matches.group(1).replace('\n',' ').strip(),
                'packaging_dimensions': logistics_matches.group(2).replace('\n',' ').strip(),
                'package_volume': logistics_matches.group(3).replace('\n',' ').strip(),
                'gross_weight': logistics_matches.group(4).replace('\n',' ').strip(),

            }
        
        return logistics_dict


    def get_full_dataframe(self):

        data_dict_list = []
        for file in self.data_file_list:
            filename = os.path.join(self.file_location, file)  # Getting full filename
            loader = PyPDFLoader(filename)                # Using LangChain PDF loader to read text from the PDF
            pages = loader.load_and_split()
            
            # Extracting product description
            product_data_dict = {}
            product_data_dict = self.get_product_data(pages)

            # Extracting technical details
            tech_data_dict = {}
            tech_data_dict = self.get_technical_data(pages, self.tech_titles_dict)
            full_tech_dict = yaml_reader.rollout_dict(tech_data_dict, {})
            
            # Extracting logistic details
            logistics_data_dict = {}
            logistics_data_dict = self.get_logistics_data(pages)

            # Combining the data dictionaries
            data_dict = {**product_data_dict, **full_tech_dict, **logistics_data_dict}
            data_dict_list.append(data_dict)

        return pd.DataFrame(data_dict_list)
