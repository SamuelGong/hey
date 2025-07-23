import re
import uuid
from typing import (
    TYPE_CHECKING,
    Collection,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from hey.mcp_tools.camel.embeddings import BaseEmbedding, OpenAIEmbedding
from hey.mcp_tools.camel.retrievers.vector_retriever import VectorRetriever
from hey.mcp_tools.camel.storages import (
    BaseVectorStorage,
    MilvusStorage,
    QdrantStorage,
)
from hey.mcp_tools.camel.types import StorageType
from hey.mcp_tools.camel.utils import Constants

if TYPE_CHECKING:
    from unstructured.documents.elements import Element

