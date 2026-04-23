"""向量数据库 DAO 抽象基类。

定义统一的数据访问接口，所有向量数据库适配器必须实现这些方法。
更换数据库时只需新增一个实现类，业务代码无需修改。
"""

from abc import ABC, abstractmethod

from langchain_core.documents import Document


class VectorStoreDAO(ABC):
    """向量数据库数据访问层抽象基类。"""

    @abstractmethod
    def store_documents(
        self, docs: list[Document], collection_name: str
    ) -> None:
        """将文档块向量化并存入数据库。

        Args:
            docs: LangChain Document 列表。
            collection_name: 集合名称。
        """

    @abstractmethod
    def search(
        self, query: str, collection_name: str, top_k: int = 4
    ) -> list[Document]:
        """根据查询文本检索最相关的文档块。

        Args:
            query: 用户查询文本。
            collection_name: 集合名称。
            top_k: 返回的最相关文档数量。

        Returns:
            相关 Document 列表。
        """

    @abstractmethod
    def get_retriever(self, collection_name: str, top_k: int = 4):
        """获取 LangChain 检索器，用于接入 Chain。

        Args:
            collection_name: 集合名称。
            top_k: 检索数量。

        Returns:
            LangChain Retriever 实例。
        """

    @abstractmethod
    def list_collections(self) -> list[str]:
        """列出所有集合名称。"""

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """删除指定集合。"""

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在。"""
