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
        """将文档向量化并存入 Qdrant（自动去重）。

        去重策略（双保险）：
        1. 按来源文件删旧：同一文件重新加载时，先删除旧版本的所有 chunk
        2. 内容哈希 ID：完全相同的内容不会重复存储
        """
        import hashlib

        # ─── 按来源删旧（处理"改了一点点"的情况） ───
        sources = {doc.metadata.get("source") for doc in docs if doc.metadata.get("source")}
        if self.collection_exists(collection_name):
            for source in sources:
                self.delete_by_source(source, collection_name)

        # 为每个文档生成确定性 ID（相同内容 → 相同 ID → 覆盖）
        ids = [
            hashlib.md5(doc.page_content.encode()).hexdigest()
            for doc in docs
        ]

        # 如果 collection 不存在，先创建空的
        if not self.collection_exists(collection_name):
            dim = self._get_embedding_dimension()
            from qdrant_client.models import Distance, VectorParams
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"📁 已创建集合 [{collection_name}] (dim={dim})")

        # 用 add_documents + ids 入库（upsert 语义）
        vs = self._get_vectorstore(collection_name)
        vs.add_documents(docs, ids=ids)
        logger.info(f"📦 已存入 {len(docs)} 个文档块到 [{collection_name}]（去重模式）")

    def search(
        self, query: str, collection_name: str, top_k: int = 4
    ) -> list[Document]:
        """从 Qdrant 检索最相关的文档块。"""
        vs = self._get_vectorstore(collection_name)
        results = vs.similarity_search(query, k=top_k)
        logger.debug(f"🔍 检索 [{collection_name}] query='{query[:30]}...' top_k={top_k} → {len(results)} 条结果")
        return results

    def search_with_scores(
        self, query: str, collection_name: str, top_k: int = 10
    ) -> list[tuple[Document, float]]:
        """从 Qdrant 检索文档块并返回相关度分数。"""
        vs = self._get_vectorstore(collection_name)
        results = vs.similarity_search_with_relevance_scores(query, k=top_k)
        logger.debug(
            f"🔍 带分数检索 [{collection_name}] query='{query[:30]}...' "
            f"top_k={top_k} → {len(results)} 条结果"
        )
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

    def delete_by_source(self, source: str, collection_name: str) -> int:
        """删除指定来源文件的所有文档。"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        if not self.collection_exists(collection_name):
            return 0

        # 先查出有多少条
        count_result = self.client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="metadata.source", match=MatchValue(value=source))]
            ),
        )
        count = count_result.count

        if count > 0:
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="metadata.source", match=MatchValue(value=source))]
                ),
            )
            logger.info(f"🗑️  已删除来源 [{source}] 的 {count} 条文档")

        return count

    def _get_vectorstore(self, collection_name: str) -> QdrantVectorStore:
        """获取已有集合的 VectorStore 实例。"""
        return QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            url=self.url,
            collection_name=collection_name,
        )

    def _get_embedding_dimension(self) -> int:
        """动态获取当前 Embedding 模型的向量维度。"""
        sample_vector = self.embeddings.embed_query("test")
        return len(sample_vector)
