import ast
from llm_agents import yaml_reader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate


class QueryParser:

    def __init__(self, query_prompt_path, api_key):

        self.query_prompt_data = yaml_reader.read(query_prompt_path)
        self.openai_api_key = open(api_key, 'r').read()
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", api_key=self.openai_api_key)


    def parse_query(self, query):
        
        query_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("human", "{input}"),
                ("ai", "{output}"),
            ]
        )

        query_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=query_prompt_template,
            examples=self.query_prompt_data['few_shot_examples'],
        )

        full_query_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.query_prompt_data['system_instructions']),
                query_prompt,
                ("human", "{input}"),
            ]
        )

        query_chain = full_query_prompt | self.llm
        query_response = query_chain.invoke({"input": query})
        query_dict = ast.literal_eval(query_response.content)
        return query_dict
