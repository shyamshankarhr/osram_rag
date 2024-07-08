from llm_agents import yaml_reader
from fuzzywuzzy import process
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import numpy as np
import ast
import re

class DataRetriever:

    def __init__(self, user_query, doc_structure_path):
        
        self.user_query = user_query 
        self.doc_titles_dict = yaml_reader.read(doc_structure_path)
        self.operator_list = ['equal', 'not equal', 'greater than', 'less than', 'greater than or equal', 'less than or equal']
        self.sentence_transformer_model = SentenceTransformer('all-MiniLM-L6-v2')


    def get_column_match(self, check_column, df, doc_titles_dict):  # select best match column to filter
    
        column_values = df.columns.tolist()
        
        if check_column in column_values:
            return check_column
        
        # Lexical matching of values in the column
        lexical_best_match, lexical_score = process.extractOne(check_column, column_values)
        
        # Getting description of each column for semantic matching
        doc_titles_dict_unrolled = yaml_reader.rollout_dict(doc_titles_dict, {})

        column_descriptions = {}
        for col in df.columns:
            column_descriptions[col] = col + ' : ' + doc_titles_dict_unrolled.get(col, col.replace('_',' '))+ ' - ' + ', '.join(data_df[col].unique().astype(str).tolist()[:3])
        
        
        # Semantic matching of values in the column using the description of each column
        input_embedding = self.sentence_transformer_model.encode(check_column, convert_to_tensor=True)
        value_embeddings = self.sentence_transformer_model.encode([column_descriptions[i] for i in column_values], convert_to_tensor=True)
        
        semantic_scores = util.pytorch_cos_sim(input_embedding, value_embeddings)[0]
        best_match_idx = semantic_scores.argmax().item()
        semantic_best_match = column_values[best_match_idx]
        semantic_score = semantic_scores[best_match_idx].item()
        
        # Combining lexical and semantic scores with 50:50 weightage
        combined_scores = [(lexical_best_match, lexical_score * 0.5 + semantic_score * 0.5),
                            (semantic_best_match, semantic_score * 0.5 + lexical_score * 0.5)]

        best_match = max(combined_scores, key=lambda x: x[1])[0]
        
        return best_match
    

    def get_value_match(self, value, column, df):  # selects best match value within a column (for string filters)
        
        
        if isinstance(column, str):
            column_values = df[column].unique().tolist()
        elif isinstance(column, list):
            column_values = column
        else:
            print('Error in column to match')  # TODO: Error message
            return False
        
        if value in column_values:
            return value
            
        # Lexical matching of values in the column
        lexical_best_match, lexical_score = process.extractOne(value, column_values)
        
        # Semantic matching of values in the column
        input_embedding = self.sentence_transformer_model.encode(value, convert_to_tensor=True)
        value_embeddings = self.sentence_transformer_model.encode(column_values, convert_to_tensor=True)
        
        semantic_scores = util.pytorch_cos_sim(input_embedding, value_embeddings)[0]
        best_match_idx = semantic_scores.argmax().item()
        semantic_best_match = column_values[best_match_idx]
        semantic_score = semantic_scores[best_match_idx].item()
        
        # Combining lexical and semantic scores with 70:30 weightage
        combined_scores = [(lexical_best_match, lexical_score * 0.7 + semantic_score * 0.3),
                            (semantic_best_match, semantic_score * 0.7 + lexical_score * 0.3)]

        best_match = max(combined_scores, key=lambda x: x[1])[0]
        return best_match


    @staticmethod
    def process_numeric_filter(df, column, value, operator, verbose=True):
        
        if operator == 'equal':
            filter_line = "df[df[%s]==%s]" %(column, value)
            df = df[df[column]==value]
            
        elif operator == 'not equal':
            filter_line = "df[df[%s]!=%s]" %(column, value)
            df = df[df[column]!=value]
            
        elif operator == 'greater than':
            filter_line = "df[df[%s]>%s]" %(column, value)
            df = df[df[column]>value]
            
        elif operator == 'less than':
            filter_line = "df[df[%s]<%s]" %(column, value)
            df = df[df[column]<value]
            
        elif operator == 'greater than or equal':
            filter_line = "df[df[%s]>=%s]" %(column, value)
            df = df[df[column]>=value]
            
        else:
            filter_line = "df[df[%s]<=%s]" %(column, value)
            df = df[df[column]<=value]
        
        if verbose:
            print('Filter operation:', filter_line)
        
        return df


    @staticmethod
    def process_string_filter(df, column, value, operator, verbose=True):
        
        if operator == 'equal':
            filter_line = "df[df[%s]=='%s']" %(column, value)
            df = df[df[column]==value]
            
        elif operator == 'not equal':
            filter_line = "df[df[%s]!='%s']" %(column, value)
            df = df[df[column]!=value]
            
        else:
            print('Operation: "%s" can\'t be done on column: %s' %(operator, column)) 
        
        if verbose:
            print('Filter operation:', filter_line)
            
        return df


    def apply_column_filter(self, df, column, value, operator, verbose=True):  # Chooses filter type for the column (string / numeric) 

        # Checking column type:
        if df[column].dtype in [np.float64, np.int64]:  # Numeric filter

            # Process filter value as a number if column type is numeric
            numeric_value = re.findall(r'-?\d+\.?\d*', value)
            numeric_value = ast.literal_eval(''.join(numeric_value))

            df = self.process_numeric_filter(df, column, numeric_value, operator, verbose)

        else:  # String filter

            value = self.get_value_match(value, column, df)  # Finding best match (not exact match)
            df = self.process_string_filter(df, column, value, operator, verbose)
        
        return df


    def apply_metadata_filters(self, query_dict, df, verbose = True):
        
        filter_df = df.copy(deep=True) 
        
        retrieval_columns = ['product_name']
        for key in query_dict:
            try:
                if query_dict[key][0] != 'unknown':  # filter column
                    column = self.get_column_match(key, df, self.doc_titles_dict)  # finding exact column
                    value = query_dict[key][0]
                    operator = self.get_value_match(query_dict[key][1], self.operator_list, df)  # finding exact operator
                    filter_df = self.apply_column_filter(filter_df, column, value, operator, verbose)
                    retrieval_columns.append(column)  # adding filter columns too, to the retrieved columns
                else:  # retrieval column
                    if key not in df.columns:
                        retrieval_columns.append(self.get_column_match(self.user_query, df, self.doc_titles_dict))
                    else:
                        retrieval_columns.append(key)
            except:
                pass
        
        retrieval_columns = list(set(retrieval_columns))
        
        if len(retrieval_columns) == 1:  # single column retrieval
            retrieved_data = {retrieval_columns[0]: filter_df[retrieval_columns[0]].tolist()}
        else:
            retrieved_data = list(filter_df[retrieval_columns].T.to_dict().values())

        return retrieved_data
