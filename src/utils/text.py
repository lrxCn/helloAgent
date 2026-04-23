"""通用文本解析工具。"""

import re


def parse_names(args: list[str]) -> list[str]:
    """将参数列表按中英文逗号和空格拆分，返回去重后的名称列表。"""
    names = []
    for arg in args:
        parts = re.split(r"[,，\s]+", arg)
        names.extend(p for p in parts if p)
    # 去重但保持顺序
    return list(dict.fromkeys(names))
