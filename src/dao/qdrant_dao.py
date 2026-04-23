"""Qdrant 向量数据库 DAO 实现。"""

import logging

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
)
from dao.base import VectorStoreDAO

logger = logging.getLogger(__name__)


class QdrantDAO(VectorStoreDAO):
    """Qdrant 向量数据库适配器。"""

    def __init__(self):
        self.client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
        self.url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        logger.debug(f"QdrantDAO 初始化: {self.url}, embedding={EMBEDDING_MODEL}")

    def store_documents(
        self, docs: list[Document], collection_name: str
    ) -> None:
        """将文档向量化并存入 Qdrant。"""
        QdrantVectorStore.from_documents(
            docs,
            embedding=self.embeddings,
            url=self.url,
            collection_name=collection_name,
        )
        logger.info(f"📦 已存入 {len(docs)} 个文档块到 [{collection_name}]")

    def search(
        self, query: str, collection_name: str, top_k: int = 4
    ) -> list[Document]:
        """从 Qdrant 检索最相关的文档块。"""
        vs = self._get_vectorstore(collection_name)
        results = vs.similarity_search(query, k=top_k)
        logger.debug(f"🔍 检索 [{collection_name}] query='{query[:30]}...' top_k={top_k} → {len(results)} 条结果")
        return results

    def get_retriever(self, collection_name: str, top_k: int = 4):
        """获取 LangChain Retriever。"""
        vs = self._get_vectorstore(collection_name)
        return vs.as_retriever(search_kwargs={"k": top_k})

    def list_collections(self) -> list[str]:
        """列出所有集合名称。"""
        collections = self.client.get_collections().collections
        return sorted(col.name for col in collections)

    def delete_collection(self, collection_name: str) -> None:
        """删除指定集合。"""
        self.client.delete_collection(collection_name=collection_name)
        logger.info(f"🗑️  已删除集合: {collection_name}")

    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在。"""
        return collection_name in self.list_collections()

    def _get_vectorstore(self, collection_name: str) -> QdrantVectorStore:
        """获取已有集合的 VectorStore 实例。"""
        return QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            url=self.url,
            collection_name=collection_name,
        )
