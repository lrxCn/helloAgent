"""哈希工具函数 - 用于生成确定性内容 ID。"""

import hashlib
import uuid

from langchain_core.documents import Document


def generate_content_hash_id(content: str | Document) -> str:
    """
    基于内容生成确定性 UUID。

    相同内容始终生成相同的 ID，用于增量同步时识别重复/未改动的文档。

    Args:
        content: 字符串或 Document 对象

    Returns:
        确定性 UUID 字符串

    Example:
        >>> generate_content_hash_id("hello world")
        'a-constant-uuid-string'
        >>> generate_content_hash_id(Document(page_content="hello world"))
        'same-constant-uuid-string'
    """
    if isinstance(content, str):
        content_str = content
    elif isinstance(content, Document):
        content_str = content.page_content
    else:
        raise TypeError(f"Unsupported content type: {type(content)}")

    # SHA256 哈希内容
    hash_hex = hashlib.sha256(content_str.encode()).hexdigest()

    # 基于哈希生成确定性 UUID5
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_hex))
