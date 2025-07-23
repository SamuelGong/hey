from abc import ABC, abstractmethod, ABCMeta


class BaseAgent(metaclass=ABCMeta):
    @abstractmethod
    def serve(self, query):
        pass
