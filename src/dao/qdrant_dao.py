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
from utils.hash import generate_content_hash_id
from utils.logger import log_function

logger = logging.getLogger(__name__)


class QdrantDAO(VectorStoreDAO):
    """Qdrant 向量数据库适配器。"""

    def __init__(self):
        self.client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
        self.url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        
        # 立即检查连接性
        try:
            self.client.get_collections()
        except Exception as e:
            logger.error(f"无法连接到 Qdrant: {e}")
            raise ConnectionError(
                f"\n{'!'*50}\n"
                f"❌ 无法连接到 Qdrant 向量数据库！\n"
                f"地址: {self.url}\n"
                f"原因: 请确保 Qdrant 服务已启动 (例如运行: docker compose up -d)\n"
                f"{'!'*50}\n"
            )

        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        logger.debug(f"QdrantDAO 初始化成功: {self.url}, embedding={EMBEDDING_MODEL}")

    @log_function
    def store_documents(
        self, docs: list[Document], collection_name: str
    ) -> None:
        """将文档向量化并存入 Qdrant（使用 LangChain Indexing API 实现增量去重）。"""
        from langchain_core.indexing import index
        from dao import get_record_manager

        if not docs:
            return

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

        vs = self._get_vectorstore(collection_name)
        record_manager = get_record_manager(f"qdrant/{collection_name}")
        
        # 使用 Indexing API 进行同步
        # cleanup="incremental" 会自动对比 source_id_key，删除旧段落、加入新段落、跳过未改动段落
        index_result = index(
            docs,
            record_manager,
            vs,
            cleanup="incremental",
            source_id_key="source",
            key_encoder=generate_content_hash_id,
        )
        
        logger.info(
            f"📦 增量同步完成 [{collection_name}]: "
            f"新增 {index_result['num_added']}, "
            f"更新 {index_result['num_updated']}, "
            f"跳过 {index_result['num_skipped']}, "
            f"删除 {index_result['num_deleted']}"
        )

    @log_function
    def search(
        self, query: str, collection_name: str, top_k: int = 4, filter: dict = None
    ) -> list[Document]:
        """从 Qdrant 检索最相关的文档块。"""
        vs = self._get_vectorstore(collection_name)
        
        # 处理 Qdrant 过滤条件
        qdrant_filter = None
        if filter:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            must_conditions = []
            for key, value in filter.items():
                must_conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                )
            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)
        
        results = vs.similarity_search(query, k=top_k, filter=qdrant_filter)
        logger.debug(f"🔍 检索 [{collection_name}] query='{query[:30]}...' filter={filter} top_k={top_k} → {len(results)} 条结果")
        return results

    @log_function
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

    def delete_by_session(self, session_id: str, collection_name: str) -> int:
        """删除指定会话的所有文档。"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        if not self.collection_exists(collection_name):
            return 0

        # 先查出有多少条
        count_result = self.client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="metadata.session_id", match=MatchValue(value=session_id))]
            ),
        )
        count = count_result.count

        if count > 0:
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="metadata.session_id", match=MatchValue(value=session_id))]
                ),
            )
            logger.info(f"🗑️  已从 [{collection_name}] 中删除会话 [{session_id}] 的 {count} 条记录")

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
