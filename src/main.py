"""AI 读书笔记助手 — 主入口。"""

import logging

from core.loader import load_and_split
from dao import get_dao
from utils.logger import setup_logging

logger = logging.getLogger(__name__)

COLLECTION_NAME = "reading_notes"


def main():
    # 初始化日志系统（会自动清理过期日志）
    setup_logging()

    logger.info("🚀 AI 读书笔记助手启动")

    # 第一步：加载并切分文档
    chunks = load_and_split("data/sample.txt")

    # 第二步：向量化并存入数据库
    dao = get_dao()
    dao.store_documents(chunks, COLLECTION_NAME)

    # 第三步：验证 — 检索测试
    query = "此恨期"
    results = dao.search(query, COLLECTION_NAME, top_k=2)
    logger.info(f"🔍 检索测试 query='{query}' → {len(results)} 条结果:")
    for i, doc in enumerate(results):
        preview = doc.page_content[:80].replace("\n", " ")
        logger.info(f"  [{i+1}] {preview}...")


if __name__ == "__main__":
    main()
