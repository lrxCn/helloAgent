"""AI 读书笔记助手 — 主入口。"""

import logging

from core.chat import chat_loop
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("🚀 AI 读书笔记助手启动")
    chat_loop()


# ─── 以下为旧版测试代码（文档加载 + 向量化 + 检索） ───
# from core.loader import load_and_split
# from dao import get_dao
#
# COLLECTION_NAME = "reading_notes"
#
# def _test_vectorstore():
#     """测试文档加载、向量化存储和检索。"""
#     chunks = load_and_split("data/sample.txt")
#     dao = get_dao()
#     dao.store_documents(chunks, COLLECTION_NAME)
#
#     query = "杨贵妃"
#     results = dao.search(query, COLLECTION_NAME, top_k=2)
#     logger.info(f"🔍 检索测试 query='{query}' → {len(results)} 条结果:")
#     for i, doc in enumerate(results):
#         preview = doc.page_content[:80].replace("\n", " ")
#         logger.info(f"  [{i+1}] {preview}...")


if __name__ == "__main__":
    main()
