from abc import abstractmethod, ABCMeta


class BaseLLM(metaclass=ABCMeta):
    @abstractmethod
    def get_response(self, user_query, system_prompt=None):
        pass
