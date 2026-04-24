"""文档加载与切分模块。

使用 LangChain 的 TextLoader 加载文本文件，
使用 RecursiveCharacterTextSplitter 将长文档切分为适合检索的小块。
"""

import logging
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import DATA_DIR
from utils.logger import log_function

logger = logging.getLogger(__name__)


@log_function
def load_and_split(
    file_path: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list:
    """加载单个文本文件并切分为文档块。

    Args:
        file_path: 文本文件路径。
        chunk_size: 每个文档块的最大字符数。
        chunk_overlap: 相邻文档块之间的重叠字符数，避免切断语义。

    Returns:
        切分后的 Document 列表。
    """
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()
    logger.info(f"📄 已加载文件: {file_path}")
    logger.debug(f"   原始文档数: {len(docs)}, 总字符数: {sum(len(d.page_content) for d in docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"✂️  切分完成: {len(chunks)} 个文档块 (chunk_size={chunk_size}, overlap={chunk_overlap})")

    return chunks


@log_function
def load_all_txt(
    data_dir: str | Path = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list:
    """扫描目录下所有 .txt 文件，加载并切分。

    Args:
        data_dir: 数据目录路径，默认使用 config 中的 DATA_DIR。
        chunk_size: 每个文档块的最大字符数。
        chunk_overlap: 相邻文档块之间的重叠字符数。

    Returns:
        所有文件切分后的 Document 列表。
    """
    data_dir = Path(data_dir) if data_dir else DATA_DIR

    if not data_dir.exists():
        logger.warning(f"数据目录不存在: {data_dir}")
        return []

    txt_files = sorted(data_dir.glob("*.txt"))
    if not txt_files:
        logger.warning(f"数据目录中没有 .txt 文件: {data_dir}")
        return []

    logger.info(f"📂 扫描到 {len(txt_files)} 个 txt 文件: {[f.name for f in txt_files]}")

    all_chunks = []
    for file_path in txt_files:
        try:
            chunks = load_and_split(str(file_path), chunk_size, chunk_overlap)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"加载文件失败 [{file_path.name}]: {e}")

    logger.info(f"📚 全部加载完成: {len(txt_files)} 个文件 → {len(all_chunks)} 个文档块")
    return all_chunks
