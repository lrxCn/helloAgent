"""文档加载与切分模块。

使用 LangChain 的 TextLoader 加载文本文件，
使用 RecursiveCharacterTextSplitter 将长文档切分为适合检索的小块。
"""

import logging

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import log_function

logger = logging.getLogger(__name__)


@log_function
def load_and_split(
    file_path: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list:
    """加载文本文件并切分为文档块。

    Args:
        file_path: 文本文件路径。
        chunk_size: 每个文档块的最大字符数。
        chunk_overlap: 相邻文档块之间的重叠字符数，避免切断语义。

    Returns:
        切分后的 Document 列表。
    """
    # 第一步：加载文件
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()
    logger.info(f"📄 已加载文件: {file_path}")
    logger.debug(f"   原始文档数: {len(docs)}, 总字符数: {sum(len(d.page_content) for d in docs)}")

    # 第二步：切分文档
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"✂️  切分完成: {len(chunks)} 个文档块 (chunk_size={chunk_size}, overlap={chunk_overlap})")

    return chunks

