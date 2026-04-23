"""向量数据库 DAO 层。

通过 get_dao() 工厂函数获取 DAO 实例，
业务代码无需关心底层使用的是哪个向量数据库。
"""

from dao.base import VectorStoreDAO


def get_dao() -> VectorStoreDAO:
    """根据配置返回对应的向量数据库 DAO 实例。

    当前支持: qdrant
    未来可扩展: faiss, milvus, chroma 等
    """
    from config.settings import VECTOR_DB_TYPE

    if VECTOR_DB_TYPE == "qdrant":
        from dao.qdrant_dao import QdrantDAO
        return QdrantDAO()

    raise ValueError(
        f"不支持的向量数据库类型: '{VECTOR_DB_TYPE}'。"
        f"请在 .env 中设置 VECTOR_DB_TYPE=qdrant"
    )
