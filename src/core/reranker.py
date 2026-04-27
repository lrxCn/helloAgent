"""Rerank 重排序模块。

向量检索是"粗筛"，Rerank 是"精排"：
- 向量检索：通过向量距离快速召回候选文档（快但粗糙）
- Rerank：用交叉编码器逐条对比 query 和文档的语义相关性（慢但精准）

流程：向量检索 Top N → Rerank 重排 → 过滤低分 → 取 Top K
"""

import logging

import httpx
from langchain_core.documents import Document, BaseDocumentCompressor
from langchain_core.callbacks.manager import Callbacks
from pydantic import Field, ConfigDict
from typing import Sequence, Optional

from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, RERANK_MODEL, RELEVANCE_THRESHOLD

logger = logging.getLogger(__name__)


def rerank(
    query: str,
    docs: list[Document],
    top_n: int = 3,
    threshold: float = None,
) -> list[tuple[Document, float]]:
    """使用 Rerank 模型对文档进行精排。

    Args:
        query: 用户查询文本。
        docs: 粗筛后的候选文档列表。
        top_n: 返回的最终文档数量。
        threshold: 相关度阈值，低于此值的文档将被丢弃。默认使用配置值。

    Returns:
        (Document, rerank_score) 元组列表，按分数降序排列。
    """
    if not docs:
        return []

    if threshold is None:
        threshold = RELEVANCE_THRESHOLD

    # 调用 Rerank API（SiliconFlow 兼容接口）
    texts = [doc.page_content for doc in docs]

    try:
        response = httpx.post(
            f"{OPENAI_BASE_URL}/rerank",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": RERANK_MODEL,
                "query": query,
                "documents": texts,
                "top_n": len(docs),  # 先拿全部分数，后面再过滤
                "return_documents": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning(f"Rerank API 调用失败，跳过重排: {e}")
        # 降级：直接返回原始文档（不重排）
        return [(doc, 1.0) for doc in docs[:top_n]]

    # 解析结果：按 rerank 分数排序，过滤低分
    all_scores = []
    results = []
    for item in data.get("results", []):
        idx = item["index"]
        score = item["relevance_score"]
        preview = docs[idx].page_content[:40].replace("\n", " ")
        all_scores.append(f"  {score:.4f} | {preview}...")
        if score >= threshold:
            results.append((docs[idx], score))

    # 按分数降序，取 top_n
    results.sort(key=lambda x: x[1], reverse=True)
    results = results[:top_n]

    logger.info(
        f"🔄 Rerank 完成: {len(docs)} 篇候选 → {len(results)} 篇通过 "
        f"(threshold={threshold}, model={RERANK_MODEL})"
    )
    for line in all_scores:
        logger.info(line)

    return results


class BGERerankCompressor(BaseDocumentCompressor):
    """自定义 BGE Reranker 压缩器，用于 LangChain 的 ContextualCompressionRetriever。"""
    top_n: int = Field(default=3, description="重排后保留的文档数量")
    threshold: Optional[float] = Field(default=None, description="相关度阈值，低于此值的文档将被丢弃")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """对文档进行重排并返回。"""
        if not documents:
            return []
        
        results = rerank(query, list(documents), top_n=self.top_n, threshold=self.threshold)
        
        final_docs = []
        for doc, score in results:
            doc_copy = Document(page_content=doc.page_content, metadata=doc.metadata.copy())
            doc_copy.metadata["relevance_score"] = score
            final_docs.append(doc_copy)
            
        return final_docs

