from munch import DefaultMunch
from abc import abstractmethod, ABCMeta

from hey.backend.llm.registry import get_llm


def extract_code_from_string(text, code_type):
    code = ""
    code_type_str = '```' + code_type.lower()
    if code_type_str in text:
        code = text.split(code_type_str)[1].split('```')[0]
    elif '```' in code:
        code = text.split('```')[1].split('```')[0]
    else:
        raise NotImplementedError
    return code.strip('\n ')


class Basic(metaclass=ABCMeta):
    def __init__(self):
        llm_config = {
            "type": "openai",
            "api_key_type": "ark",
            "model_name": "ep-20250212105505-5zlbx",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3"
        }  # TODO: avoid hard-coding
        llm_config = DefaultMunch.fromDict(llm_config)
        self.coding_llm = get_llm(llm_config)

    def serve(self, query):
        code = self.generate_code(query)
        result = self.execute_code(code)
        return result

    @abstractmethod
    def generate_code(self, query):
        pass

    @abstractmethod
    def execute_code(self, code):
        pass
