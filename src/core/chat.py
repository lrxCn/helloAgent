"""AI 问答模块 — 智能 RAG。"""

import logging

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI
from prompt_toolkit import prompt

from config.settings import (
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME, SYSTEM_PROMPT,
    RAG_TOP_K, RAG_RECALL_K, COLLECTION_NAME,
)
from core.loader import load_all_txt
from core.reranker import BGERerankCompressor
from langchain_classic.retrievers import ContextualCompressionRetriever
from core.memory import MultiLayerMemory
from dao import get_dao

logger = logging.getLogger(__name__)


class SmartAgent:
    """智能问答代理，自动管理知识库检索与模式切换。"""

    def __init__(self, dao=None, llm=None):
        # 1. 初始化基础依赖
        try:
            self.dao = dao or get_dao()
        except (ConnectionError, ValueError) as e:
            print(e)
            import sys
            sys.exit(1)

        self.llm = llm or ChatOpenAI(
            model=OPENAI_MODEL_NAME,
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        
        # 2. 初始化记忆系统
        self.memory = MultiLayerMemory(dao=self.dao, llm=self.llm)

        # 3. 构建处理链
        # 注意：这里我们手动组装 Prompt，因为逻辑变复杂了
        self.system_prompt_template = (
            "{base_system_prompt}\n\n"
            "--- 记忆上下文 ---\n"
            "【历史摘要】：\n{summary}\n\n"
            "【相关历史片段】：\n{long_term_memory}\n"
            "------------------\n"
        )
        
        logger.info(f"💬 问答链已构建 (model={OPENAI_MODEL_NAME}, memory=MultiLayer)")

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
            # 1. 获取基础检索器 (粗排)
            base_retriever = self.dao.get_retriever(collection_name=COLLECTION_NAME, top_k=RAG_RECALL_K)
            
            # 2. 获取压缩器 (精排)
            compressor = BGERerankCompressor(top_n=RAG_TOP_K)
            
            # 3. 组合成上下文压缩检索器
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            
            # 4. 执行检索并自动完成粗排+精排
            return compression_retriever.invoke(question)

        except Exception as e:
            logger.warning(f"检索/Rerank 失败，降级为普通问答: {e}")
            return []

    def answer(self, question: str) -> str:
        """核心问答逻辑：动态组装记忆、知识库并调用 LLM。"""
        # 1. 检索知识库 (RAG)
        docs = self.get_relevant_docs(question)
        if docs:
            logger.info(f"📚 RAG 模式回答 (参考了 {len(docs)} 篇文档)")

        # 2. 获取分层记忆
        summary = self.memory.get_mid_term_summary()
        long_term = self.memory.get_long_term_memories(question)
        short_term = self.memory.get_short_term_messages()

        # 3. 组装基础系统提示词
        final_system_prompt = self.system_prompt_template.format(
            base_system_prompt=SYSTEM_PROMPT,
            summary=summary if summary else "（暂无相关摘要）",
            long_term_memory=long_term if long_term else "（暂无相关历史片段）"
        )

        # 4. 动态构建提示词模板并调用 LLM
        if docs:
            sys_msg = final_system_prompt + "\n\n【参考资料】\n{context}"
        else:
            sys_msg = final_system_prompt

        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_msg),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

        if docs:
            # 确保元数据包含 source 字段以适配模板
            for d in docs:
                if "source" not in d.metadata:
                    d.metadata["source"] = "未知文档"

            document_prompt = PromptTemplate(
                input_variables=["page_content", "source"],
                template="[来源：{source}]\n{page_content}"
            )
            rag_chain = create_stuff_documents_chain(
                llm=self.llm,
                prompt=prompt,
                document_prompt=document_prompt,
                document_variable_name="context",
                document_separator="\n\n---\n\n"
            )
            response = rag_chain.invoke({
                "context": docs,
                "chat_history": short_term,
                "question": question
            })
        else:
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "chat_history": short_term,
                "question": question
            })

        # 5. 持久化当前轮次到记忆系统
        self.memory.add_message(HumanMessage(content=question))
        self.memory.add_message(AIMessage(content=response))

        return response


def chat_loop(dao=None, llm=None):
    """交互式问答主循环。"""
    agent = SmartAgent(dao=dao, llm=llm)

    # 启动时自动同步知识库
    if not agent.sync_knowledge_base():
        print("⚠️  未加载到新文档，将使用已有知识库")

    print("\n" + "=" * 50)
    print("  💬 AI 智能问答助手")
    print("  基础命令: /quit")
    print("  记忆管理: /m, /mem, /memory")
    print("    -s, -short  [ -d ]  查看/删除短期记忆 (SQL)")
    print("    -m, -middle [ -d ]  查看/删除中期摘要 (Summary)")
    print("    -l, -long   [ -d ]  查看/删除长期记忆 (Vector)")
    print("    -d, -delete         删除全部分层记忆")
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

        # 处理记忆查询与管理命令
        if question.startswith(("/m", "/mem", "/memory")):
            parts = question.split()
            args = [a.lower() for a in parts[1:]]
            
            if not args:
                print("💡 用法: /m [-s|-m|-l] [-d]")
                continue
            
            # 1. 处理全量删除: /m -d
            if len(args) == 1 and args[0] in ("-d", "-delete"):
                agent.memory.clear_all()
                print("🧹 已成功清空当前会话的所有记忆（短/中/长期）。")
                continue

            # 2. 处理分层逻辑
            flag = args[0]
            is_delete = "-d" in args or "-delete" in args

            if flag in ("-s", "-short"):
                if is_delete:
                    agent.memory.clear_short_term()
                    print("🧹 已清空短期记忆。")
                else:
                    msgs = agent.memory.get_short_term_messages()
                    print(f"\n🧠 [短期记忆 - 最近 {len(msgs)} 条]")
                    for m in msgs:
                        role = "用户" if isinstance(m, HumanMessage) else "AI"
                        print(f"  {role}: {m.content}")
            elif flag in ("-m", "-middle"):
                if is_delete:
                    agent.memory.clear_mid_term()
                    print("🧹 已清空中期摘要。")
                else:
                    summary = agent.memory.get_mid_term_summary()
                    print(f"\n🧠 [中期摘要]")
                    print(f"  {summary if summary else '（暂无摘要）'}")
            elif flag in ("-l", "-long"):
                if is_delete:
                    agent.memory.clear_long_term()
                    print("🧹 已清空长期记忆。")
                else:
                    # 长期记忆检索需要 query
                    query = " ".join([a for a in args[1:] if not a.startswith("-")])
                    if not query: query = "重要对话记录"
                    memories = agent.memory.get_long_term_memories(query, k=5)
                    print(f"\n🧠 [长期记忆 - 检索词: '{query}']")
                    print(f"  {memories if memories else '（未检索到相关内容）'}")
            else:
                print(f"❌ 未知参数: {flag}")
            print()
            continue

        print(f"AI: {agent.answer(question)}\n")
