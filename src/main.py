"""AI 读书笔记助手 — 主入口。"""

import logging

from config.settings import OPENAI_MODEL_NAME, OPENAI_BASE_URL, OPENAI_API_KEY
from langchain_openai import ChatOpenAI
from dao import get_dao
from core.chat import chat_loop
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("🚀 AI Agent Launch!")
    
    # 1. 依赖注入：在入口处初始化全局共享的实例，避免重复创建连接
    dao = get_dao()
    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )
    
    # 2. 启动对话循环
    chat_loop(dao=dao, llm=llm)




if __name__ == "__main__":
    main()
