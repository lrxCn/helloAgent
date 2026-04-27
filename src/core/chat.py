"""AI 问答模块 — 智能 RAG。"""

import logging

from langchain_core.messages import HumanMessage, AIMessage
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
from core.memory import MultiLayerMemory
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
        
        # 2. 初始化记忆系统
        self.memory = MultiLayerMemory()

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
        """核心问答逻辑：动态组装记忆、知识库并调用 LLM。"""
        # 1. 检索知识库 (RAG)
        docs = self.get_relevant_docs(question)
        context = ""
        if docs:
            context_parts = []
            for d in docs:
                source = d.metadata.get("source", "未知文档")
                context_parts.append(f"[来源：{source}]\n{d.page_content}")
            context = "\n\n---\n\n".join(context_parts)
            logger.info(f"📚 RAG 模式回答 (参考了 {len(docs)} 篇文档)")

        # 2. 获取分层记忆
        summary = self.memory.get_mid_term_summary()
        long_term = self.memory.get_long_term_memories(question)
        short_term = self.memory.get_short_term_messages()

        # 打印记忆状态
        # print(f"🧠 [记忆状态] 短期: {short_term} 条消息 | 中期摘要: {summary} | 长期相关片段: {long_term}")

        # 3. 组装输入
        final_system_prompt = self.system_prompt_template.format(
            base_system_prompt=SYSTEM_PROMPT,
            summary=summary if summary else "（暂无相关摘要）",
            long_term_memory=long_term if long_term else "（暂无相关历史片段）"
        )

        messages = [("system", final_system_prompt)]
        # 加入短期对话历史
        for m in short_term:
            role = "human" if isinstance(m, HumanMessage) else "ai"
            messages.append((role, m.content))
        
        # 加入当前用户问题
        user_content = question
        if context:
            user_content = f"【参考资料】\n{context}\n\n我的问题是：{question}"
        
        messages.append(("human", user_content))

        # 4. 调用 LLM
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.llm | StrOutputParser()
        
        response = chain.invoke({})

        # 5. 持久化当前轮次到记忆系统
        self.memory.add_message(HumanMessage(content=question))
        self.memory.add_message(AIMessage(content=response))

        return response


def chat_loop():
    """交互式问答主循环。"""
    agent = SmartAgent()

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
