from munch import DefaultMunch
from hey.backend.llm.openai import OpenAILLM

config_dict = {
    "base_url": "http://localhost:11434/v1/",
    "model_name": "deepseek-r1:1.5b"
}
config = DefaultMunch.fromDict(config_dict)
llm = OpenAILLM(config=config)
response = llm.get_response(
    user_query="Hello"
)
print(response)