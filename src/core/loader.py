"""文档加载与切分模块。

引入专业解析库 unstructured，支持多种格式（PDF、Word、Markdown 等）。
摒弃基于字符的切分，采用 chunk_by_title 进行语义化分块。
保留丰富的元数据（Metadata）存入 Qdrant。
"""

import os
import logging
from pathlib import Path

from langchain_unstructured import UnstructuredLoader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from config.settings import DATA_DIR
from utils.logger import log_function
from utils.file_state import FileStateManager

logger = logging.getLogger(__name__)

def summarize_image(base64_image: str, llm=None) -> str:
    """调用多模态模型生成图片/图表摘要"""
    try:
        # 优先使用项目外部传入的 llm 实例，如果没有传才 fallback
        chat = llm or ChatOpenAI(model="gpt-4o-mini", max_tokens=300)
        msg = chat.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": "请详细描述这张图片或表格的内容，提取关键数据和核心信息："},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ]
                )
            ]
        )
        return msg.content
    except Exception as e:
        logger.error(f"图片摘要生成失败: {e}")
        return "[图片/图表内容提取失败]"


@log_function
def load_and_split(file_path: str, llm=None) -> list:
    """加载单个文档并进行语义化切分。

    Args:
        file_path: 文档文件路径。

    Returns:
        语义切分后的 Document 列表。
    """
    logger.info(f"📄 开始解析文件: {file_path}")
    
    # 设置项目本地的 Tesseract 语言包路径
    project_root = Path(__file__).resolve().parent.parent.parent
    os.environ["TESSDATA_PREFIX"] = str(project_root / "lang")
    
    try:
        # 使用 hi_res 策略，启用表格推断和图片多模态提取
        loader = UnstructuredLoader(
            file_path, 
            chunking_strategy="by_title",
            strategy="hi_res",
            skip_infer_table_types=[], # 开启表格推断
            extract_image_block_types=["Image", "Table"],
            extract_image_block_to_payload=True,
            languages=["chi_sim", "eng"] # 指定中英文双语识别
        )
        chunks = loader.load()
        logger.info(f"✂️ 解析与切分完成: {len(chunks)} 个语义块 (Semantic Chunks)")
        
        # 多模态与复杂元素后处理
        for chunk in chunks:
            # 1. 强化表格：如果存在 HTML 格式的表格，追加到内容中，增强 LLM 理解
            if "text_as_html" in chunk.metadata and chunk.metadata["text_as_html"]:
                chunk.page_content += f"\n\n【结构化表格】\n{chunk.metadata['text_as_html']}"
            
            # 2. 图像摘要：如果存在 base64 图像，调用大模型生成摘要并追加
            if "image_base64" in chunk.metadata and chunk.metadata["image_base64"]:
                logger.info("🖼️ 发现图片/复杂表格元素，正在生成多模态摘要...")
                summary = summarize_image(chunk.metadata["image_base64"], llm=llm)
                chunk.page_content += f"\n\n【多模态摘要】\n{summary}"
                # 处理完后移除 base64 数据以节省向量库和内存空间
                del chunk.metadata["image_base64"]
                
        if chunks:
            # 简单校验 Metadata 是否存在
            logger.debug(f"   示例块 Metadata: {chunks[0].metadata}")
            
        return chunks
    except Exception as e:
        logger.error(f"❌ 解析文件失败 [{file_path}]: {e}")
        return []


@log_function
def load_all_docs(data_dir: str | Path = None, llm=None) -> list:
    """扫描目录下所有支持的文档文件，加载并语义化切分。

    Args:
        data_dir: 数据目录路径，默认使用 config 中的 DATA_DIR。

    Returns:
        所有文件语义切分后的 Document 列表。
    """
    data_dir = Path(data_dir) if data_dir else DATA_DIR

    if not data_dir.exists():
        logger.warning(f"数据目录不存在: {data_dir}")
        return []

    # 支持扫描多种格式
    supported_extensions = ("*.txt", "*.md", "*.pdf", "*.docx", "*.html")
    doc_files = []
    for ext in supported_extensions:
        doc_files.extend(data_dir.glob(ext))
        
    # 对找到的文件进行排序
    doc_files = sorted(doc_files)

    if not doc_files:
        logger.warning(f"数据目录中没有支持的文档: {data_dir}")
        return []

    logger.info(f"📂 扫描到 {len(doc_files)} 个支持的文档文件: {[f.name for f in doc_files]}")

    # --- 文件级增量拦截逻辑 ---
    state_manager = FileStateManager(data_dir)
    sync_state = state_manager.load()

    all_chunks = []
    new_sync_state = {}
    skipped_files = 0

    for file_path in doc_files:
        try:
            mtime = file_path.stat().st_mtime
            file_key = file_path.name
            new_sync_state[file_key] = mtime
            
            # 如果文件未修改过，直接跳过本地加载和切分
            if file_key in sync_state and sync_state[file_key] == mtime:
                skipped_files += 1
                continue

            chunks = load_and_split(str(file_path), llm=llm)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"加载文件异常 [{file_path.name}]: {e}")

    # 保存最新状态
    state_manager.save(new_sync_state)

    logger.info(
        f"📚 本地文档解析完成: 共 {len(doc_files)} 个文件, "
        f"跳过未修改 {skipped_files} 个, "
        f"新增/更新切分 {len(all_chunks)} 个语义块"
    )
    return all_chunks
