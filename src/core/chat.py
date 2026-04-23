"""AI 问答模块 — 使用 LangChain 的 ChatModel + PromptTemplate + LCEL。

这是 LangChain 最核心的能力：
1. ChatOpenAI — 统一的 LLM 调用接口
2. ChatPromptTemplate — 构建提示词模板
3. LCEL（管道符 |）— 把组件串成链
4. StrOutputParser — 解析输出为纯文本
"""

import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def build_chat_chain():
    """构建基础问答链。

    LCEL 写法：prompt | llm | parser
    数据流：用户输入 → 填入模板 → 发给 LLM → 解析输出 → 返回字符串
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )

    parser = StrOutputParser()

    # LCEL 管道：这就是 LangChain 最优雅的地方
    chain = prompt | llm | parser

    logger.info(f"💬 问答链已构建 (model={OPENAI_MODEL_NAME})")
    return chain


def chat_loop():
    """交互式问答循环。"""
    chain = build_chat_chain()

    print("\n" + "=" * 50)
    print("  💬 AI 问答助手（输入 /quit 退出）")
    print("=" * 50 + "\n")

    while True:
        try:
            question = input("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 再见！")
            break

        if not question:
            continue
        if question == "/quit":
            print("👋 再见！")
            break

        logger.debug(f"用户提问: {question}")

        # 调用链
        answer = chain.invoke({"question": question})
        print(f"AI: {answer}\n")
        logger.debug(f"AI 回答: {answer[:100]}...")
