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


def get_record_manager(namespace: str):
    """获取文档增量同步状态管理器。
    
    使用 SQLRecordManager 在本地记录哪些 Chunk 已经处理过，
    从而避免将相同的文本反复发送给 OpenAI API，节省 Token 费用。
    """
    from langchain_community.indexes._sql_record_manager import SQLRecordManager
    from config.settings import DATA_DIR
    
    # 默认使用 sqlite 在 data 目录下存储同步记录
    db_url = f"sqlite:///{DATA_DIR}/record_manager_cache.sql"
    record_manager = SQLRecordManager(
        namespace=namespace,
        db_url=db_url,
    )
    # 初始化表结构
    record_manager.create_schema()
    return record_manager
