import pandas as pd
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate
from llama_index.experimental.query_engine.pandas import PandasInstructionParser
from llama_index.core.query_pipeline import (
    QueryPipeline as QP,
    Link,
    InputComponent,
)

class AnswerSynthesizer:

    def __init__(self, retrieved_data, api_key, verbose=True):

        self.retrieved_df = pd.DataFrame(retrieved_data)
        self.instruction_str = (
                "1. Convert the query to executable Python code using Pandas.\n"
                "2. The final line of code should be a Python expression that can be called with the `eval()` function.\n"
                "3. The code should represent a solution to the query.\n"
                "4. PRINT ONLY THE EXPRESSION.\n"
                "5. Do not quote the expression.\n"
            )
        self.pandas_prompt_str = (
                "You are working with a pandas dataframe in Python.\n"
                "The name of the dataframe is `df`.\n"
                "This is the result of `print(df.head())`:\n"
                "{df_str}\n\n"
                "Follow these instructions:\n"
                "{instruction_str}\n"
                "Query: {query_str}\n\n"
                "Expression:"
            )
        self.response_synthesis_prompt_str = (
                "Given an input question, synthesize a response from the query results.\n"
                "Query: {query_str}\n\n"
                "Pandas Instructions (optional):\n{pandas_instructions}\n\n"
                "Pandas Output: {pandas_output}\n\n"
                "Response: "
            )
        self.openai_api_key = open(api_key, 'r').read()
        self.llm = OpenAI(model="gpt-3.5-turbo", api_key=self.openai_api_key)
        self.verbose = verbose

        
    def synthesize_answer(self, user_query):

        pandas_prompt = PromptTemplate(self.pandas_prompt_str).partial_format(
                instruction_str=self.instruction_str, df_str=self.retrieved_df.head(5)
            )
        pandas_output_parser = PandasInstructionParser(self.retrieved_df)
        response_synthesis_prompt = PromptTemplate(self.response_synthesis_prompt_str)

        qp = QP(
            modules={
                "input": InputComponent(),
                "pandas_prompt": pandas_prompt,
                "llm1": self.llm,
                "pandas_output_parser": pandas_output_parser,
                "response_synthesis_prompt": response_synthesis_prompt,
                "llm2": self.llm,
            },
            verbose=self.verbose,
        )

        qp.add_chain(["input", "pandas_prompt", "llm1", "pandas_output_parser"])
        qp.add_links(
            [
                Link("input", "response_synthesis_prompt", dest_key="query_str"),
                Link(
                    "llm1", "response_synthesis_prompt", dest_key="pandas_instructions"
                ),
                Link(
                    "pandas_output_parser",
                    "response_synthesis_prompt",
                    dest_key="pandas_output",
                ),
            ]
        )
        # add link from response synthesis prompt to llm2
        qp.add_link("response_synthesis_prompt", "llm2")

        response = qp.run(
            query_str=user_query,
        )

        return response.message.content
