"""AI 问答模块 — 智能 RAG。"""

import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from prompt_toolkit import prompt

from config.settings import (
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME, SYSTEM_PROMPT,
    RAG_TOP_K, RAG_RECALL_K, COLLECTION_NAME,
)
from core.loader import load_all_txt
from core.reranker import rerank
from dao import get_dao

logger = logging.getLogger(__name__)


class SmartAgent:
    """智能问答代理，自动管理知识库检索与模式切换。"""

    def __init__(self):
        # 1. 初始化基础依赖
        try:
            self.dao = get_dao()
        except (ConnectionError, ValueError) as e:
            print(e)
            import sys
            sys.exit(1)

        self.llm = ChatOpenAI(
            model=OPENAI_MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        
        # 2. 构建处理链
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{user_input}"),
        ])
        self.chain = prompt | self.llm | StrOutputParser()

        logger.info(f"💬 问答链已构建 (model={OPENAI_MODEL_NAME})")



    def sync_knowledge_base(self) -> bool:
        """加载数据目录并同步到向量数据库。"""
        print("📂 正在扫描并加载数据目录下的文档...")
        try:
            chunks = load_all_txt()
            if not chunks:
                logger.warning("没有找到可加载的文档")
                return False
            self.dao.store_documents(chunks, COLLECTION_NAME)
            print("✅ 文档加载完成，已就绪")
            return True
        except Exception as e:
            logger.error(f"文档加载失败: {e}")
            print("❌ 文档加载失败")
            return False

    def get_relevant_docs(self, question: str) -> list:
        """检索并重排序相关文档。"""
        if not self.dao.collection_exists(COLLECTION_NAME):
            return []

        try:
            # 粗筛
            candidates = self.dao.search_with_scores(
                question, COLLECTION_NAME, top_k=RAG_RECALL_K
            )
            raw_docs = [doc for doc, score in candidates]
            
            if not raw_docs:
                return []

            # 精排
            reranked = rerank(question, raw_docs, top_n=RAG_TOP_K)
            return [doc for doc, score in reranked]
        except Exception as e:
            logger.warning(f"检索/Rerank 失败，降级为普通问答: {e}")
            return []

    def answer(self, question: str) -> str:
        """核心问答逻辑：动态组装输入。"""
        docs = self.get_relevant_docs(question)
        
        if docs:
            context_parts = []
            for d in docs:
                source = d.metadata.get("source", "未知文档")
                context_parts.append(f"[来源：{source}]\n{d.page_content}")
                
            context = "\n\n---\n\n".join(context_parts)
            user_input = f"【参考资料】\n{context}\n\n我的问题是：{question}"
            logger.info(f"📚 RAG 模式回答 (参考了 {len(docs)} 篇文档)")
        else:
            user_input = question
            logger.info("💬 普通模式回答（未找到相关文档）")
            
        return self.chain.invoke({"user_input": user_input})


def chat_loop():
    """交互式问答主循环。"""
    agent = SmartAgent()

    # 启动时自动同步知识库
    if not agent.sync_knowledge_base():
        print("⚠️  未加载到新文档，将使用已有知识库")

    print("\n" + "=" * 50)
    print("  💬 AI 智能问答助手")
    print("  命令: /quit")
    print("  每次提问自动判断是否基于文档回答")
    print("=" * 50 + "\n")

    while True:
        try:
            # 使用 prompt_toolkit 解决 macOS 终端中文输入与删除的编码问题
            question = prompt("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 再见！")
            break

        if not question:
            continue

        if question == "/quit":
            print("👋 再见！")
            break

        print(f"AI: {agent.answer(question)}\n")
