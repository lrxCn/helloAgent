import logging
from typing import List
from sqlalchemy import create_engine, Column, String, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from config.settings import (
    MEMORY_DB_PATH, MEMORY_WINDOW_SIZE, MEMORY_COLLECTION_NAME,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME
)
from dao import get_dao

logger = logging.getLogger(__name__)

Base = declarative_base()

class SessionSummary(Base):
    """存储会话的中期摘要。"""
    __tablename__ = "session_summaries"
    session_id = Column(String, primary_key=True)
    summary = Column(Text, default="")

class MultiLayerMemory:
    """
    分层记忆架构实现：
    1. SQL Layer: 短期原始对话 (SQLite)
    2. Summary Layer: 中期对话摘要 (SQLite)
    3. Vector Layer: 长期对话归档 (Qdrant)
    """

    def __init__(self, session_id: str = "default_session", dao=None, llm=None):
        self.session_id = session_id
        self.db_url = f"sqlite:///{MEMORY_DB_PATH}"
        
        # 1. 初始化 SQL 聊天记录存储
        self.history = SQLChatMessageHistory(
            session_id=session_id,
            connection=self.db_url
        )
        
        # 2. 初始化摘要存储表
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # 3. 初始化 LLM 和 DAO
        self.dao = dao or get_dao()
        self.llm = llm or ChatOpenAI(
            model=OPENAI_MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=0
        )

    def get_short_term_messages(self) -> List[BaseMessage]:
        """获取短期窗口内的原始消息。"""
        return self.history.messages

    def get_mid_term_summary(self) -> str:
        """获取当前会话的中期摘要。"""
        with self.Session() as session:
            res = session.query(SessionSummary).filter_by(session_id=self.session_id).first()
            return res.summary if res else ""

    def get_long_term_memories(self, query: str, k: int = 3) -> str:
        """从向量库检索相关的历史记忆。"""
        if not self.dao.collection_exists(MEMORY_COLLECTION_NAME):
            logger.warning(f"集合 {MEMORY_COLLECTION_NAME} 不存在")
            return ""
        
        # 使用 search 获取前 K 个最相关的，带上 session_id 过滤
        results = self.dao.search(
            query, 
            MEMORY_COLLECTION_NAME, 
            top_k=k, 
            filter={"session_id": self.session_id}
        )
        
        if not results:
            logger.debug(f"长期记忆检索未发现匹配项: collection={MEMORY_COLLECTION_NAME}, query={query}")
            return ""
        
        memories = []
        for doc in results:
            role = "用户" if doc.metadata.get("role") == "user" else "AI"
            memories.append(f"[{role}]: {doc.page_content}")
        
        return "\n".join(memories) if memories else ""

    def add_message(self, message: BaseMessage):
        """添加消息并触发维护逻辑。"""
        self.history.add_message(message)
        self._maintain_memory()

    def _maintain_memory(self):
        """执行滚动压缩与归档逻辑。"""
        messages = self.history.messages
        # 我们希望保留最近 MEMORY_WINDOW_SIZE 条对话（通常是 Human + AI 对，所以 * 2）
        max_messages = MEMORY_WINDOW_SIZE * 2
        
        if len(messages) > max_messages:
            # 取出超出窗口的部分进行摘要和归档
            num_to_archive = len(messages) - max_messages
            to_archive = messages[:num_to_archive]
            
            logger.info(f"💾 正在归档 {num_to_archive} 条旧消息到长期记忆...")
            
            # 1. 更新中期摘要
            current_summary = self.get_mid_term_summary()
            new_summary = self._generate_summary(current_summary, to_archive)
            self._save_summary(new_summary)
            
            # 2. 归档到向量库
            self._archive_to_vector_db(to_archive)
            
            # 3. 从 SQL 原始记录中清理
            self._truncate_sql_history(num_to_archive)

    def _generate_summary(self, old_summary: str, messages: List[BaseMessage]) -> str:
        """调用 LLM 生成更新后的摘要。"""
        new_content = "\n".join([
            f"{'用户' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" 
            for m in messages
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个记忆管理助手。请根据已有的摘要和新发生的对话内容，生成一个更加全面且精炼的对话摘要。"),
            ("human", f"已有摘要：\n{old_summary if old_summary else '（无）'}\n\n新对话内容：\n{new_content}\n\n请输出最新的完整摘要：")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({})
        return response.content

    def _save_summary(self, summary: str):
        with self.Session() as session:
            res = session.query(SessionSummary).filter_by(session_id=self.session_id).first()
            if res:
                res.summary = summary
            else:
                session.add(SessionSummary(session_id=self.session_id, summary=summary))
            session.commit()

    def _archive_to_vector_db(self, messages: List[BaseMessage]):
        docs = []
        import uuid
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "ai"
            doc = Document(
                page_content=msg.content,
                metadata={
                    "session_id": self.session_id,
                    "role": role,
                    "source": f"archive_{self.session_id}",
                    "type": "chat_history_archive",
                    "msg_id": uuid.uuid4().hex
                }
            )
            docs.append(doc)
        
        if docs:
            # 确保集合存在
            if not self.dao.collection_exists(MEMORY_COLLECTION_NAME):
                from qdrant_client.models import Distance, VectorParams
                dim = len(self.dao.embeddings.embed_query("test"))
                self.dao.client.create_collection(
                    collection_name=MEMORY_COLLECTION_NAME,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
                logger.info(f"📁 已创建记忆归档集合 [{MEMORY_COLLECTION_NAME}] (dim={dim})")

            # 对于聊天记录归档，我们不使用 DAO 的增量索引（那会导致相同内容的聊天被跳过）
            # 我们直接使用底层 VectorStore 进行添加
            vs = self.dao._get_vectorstore(MEMORY_COLLECTION_NAME)
            vs.add_documents(docs)
            logger.info(f"✅ 已成功归档 {len(docs)} 条消息到向量库。")

    def _truncate_sql_history(self, count: int):
        """从 SQLite 中删除最早的 N 条记录。"""
        from sqlalchemy import bindparam
        with self.Session() as session:
            try:
                # 获取待删除的记录 ID
                res = session.execute(text(
                    "SELECT id FROM message_store WHERE session_id = :sid ORDER BY id ASC LIMIT :count"
                ), {"sid": self.session_id, "count": count})
                ids = [row[0] for row in res.fetchall()]
                
                if ids:
                    # 使用 expanding=True 处理 IN 子句
                    stmt = text("DELETE FROM message_store WHERE id IN :ids").bindparams(
                        bindparam("ids", expanding=True)
                    )
                    session.execute(stmt, {"ids": ids})
                    session.commit()
                    logger.info(f"✅ 已从短期记忆(SQL)中移除 {len(ids)} 条归档消息。")
            except Exception as e:
                logger.error(f"清理 SQLite 消息失败: {e}")
                session.rollback()

    def clear_short_term(self):
        """清空短期对话记忆。"""
        self.history.clear()
        logger.info(f"🧹 已清空会话 [{self.session_id}] 的短期记忆。")

    def clear_mid_term(self):
        """清空中期摘要。"""
        with self.Session() as session:
            session.query(SessionSummary).filter_by(session_id=self.session_id).delete()
            session.commit()
        logger.info(f"🧹 已清空会话 [{self.session_id}] 的中期摘要。")

    def clear_long_term(self):
        """清空长期归档记忆。"""
        count = self.dao.delete_by_session(self.session_id, MEMORY_COLLECTION_NAME)
        logger.info(f"🧹 已清空会话 [{self.session_id}] 的长期记忆 (删除了 {count} 条记录)。")

    def clear_all(self):
        """清空所有层级的记忆。"""
        self.clear_short_term()
        self.clear_mid_term()
        self.clear_long_term()
