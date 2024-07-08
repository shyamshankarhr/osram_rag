from pathlib import Path
import os
from utils import english_downloader
from pdf_parser import PDFParser
import data_cleaner
from llm_agents.query_parser import QueryParser
from llm_agents.data_retriever import DataRetriever
from llm_agents.answer_synthesizer import AnswerSynthesizer
import sys


DATA_FILE_LOCATION = './../data/datafiles/'   # path containing the data files
EN_DATA_FILE_LOCATION = './../data/datafiles_en/'  # path containing english version of the original german files
DOCUMENT_STRUCTURE_PATH = './../config/doc_titles/document_structure_en.yaml'  # file with structure of titles in the data sheets
QUERY_PROMPT_PATH = './../config/prompts/query_prompt_en.yaml'  # file with few-shot learning examples for query parsing
API_KEY_PATH = './../config/api_keys/openai_key.txt'  # please use a txt file with openai api key

VERBOSE = False  # Set to True to get detailed results

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_LOCATION = os.path.join(script_dir, DATA_FILE_LOCATION)
EN_DATA_FILE_LOCATION = os.path.join(script_dir, EN_DATA_FILE_LOCATION)
DOCUMENT_STRUCTURE_PATH = os.path.join(script_dir, DOCUMENT_STRUCTURE_PATH)
QUERY_PROMPT_PATH = os.path.join(script_dir, QUERY_PROMPT_PATH)
API_KEY_PATH = os.path.join(script_dir, API_KEY_PATH)


def run_chat(user_query):

    # Query parsing
    query_parser = QueryParser(QUERY_PROMPT_PATH, API_KEY_PATH)
    query_dict = query_parser.parse_query(user_query)
    
    if VERBOSE:
        print('Metadata filters from query: %s' %str(query_dict))

    # Data retrieval
    data_retriever = DataRetriever(user_query, DOCUMENT_STRUCTURE_PATH)
    retrieved_data = data_retriever.apply_metadata_filters(query_dict, data_df, VERBOSE)

    if VERBOSE:
        print('Retrieved data: \n%s' %str(retrieved_data))
    
    # Answer synthesis
    try:
        answer_synthesizer = AnswerSynthesizer(retrieved_data, API_KEY_PATH, VERBOSE)
        answer = answer_synthesizer.synthesize_answer(user_query)
    except:
        print('Error in synthesizing response. Here is the raw result:\n')
        answer = str(retrieved_data)  # error in synthesizing response

    return answer

if __name__ == '__main__':

    print('Loading OSRAM-Chatbot')

    # Ensure Openai key file is present
    if not os.path.isfile(API_KEY_PATH):
        print('Please add openai api key file at config/api_keys/openai_key.txt')
        sys.exit(0)

    # Download english versions if not present
    if not os.path.exists(EN_DATA_FILE_LOCATION):
          english_downloader.download_english_versions(DATA_FILE_LOCATION, EN_DATA_FILE_LOCATION)
    DATA_FILE_LOCATION = EN_DATA_FILE_LOCATION
    
    # Parse datafiles into dataframe
    pdf_parser = PDFParser(DATA_FILE_LOCATION, DOCUMENT_STRUCTURE_PATH)
    data_df = pdf_parser.get_full_dataframe()
    
    # Cleaning data to normalize numeric values
    data_df = data_cleaner.clean_data(data_df)
    
    #  --- Starting chat ---
    user_query = input("Welcome to OSRAM Chatbot! How can I help you today?\n")
    answer = run_chat(user_query)
    print(answer)

    try:
        user_query = input("\nWould you like to know anything more? (You can enter 'exit' to quit)\n")
        while user_query.lower() != 'exit':
            answer = run_chat(user_query)
            print(answer)
            user_query = input("\nWould you like to know anything more? (You can enter 'exit' to quit)\n")

    except KeyboardInterrupt as e:
        print('\nExiting the chat')

    print('\nThanks for using OSRAM-Chatbot!')
