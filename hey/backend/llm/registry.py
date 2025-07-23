from hey.backend.llm.openai import OpenAILLM
from hey.backend.llm.azure import AzureLLM

registered_environments = {
    'openai': OpenAILLM,
    'azure': AzureLLM
}


def get_llm(config):
    return registered_environments[config.type](config)
