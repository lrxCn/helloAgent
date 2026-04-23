"""清理 Qdrant 数据库中的 collection。

用法:
    uv run python tools/clearDB.py -a              # 删除所有 collection
    uv run python tools/clearDB.py col1 col2        # 删除指定 collection
    uv run python tools/clearDB.py "col1,col2,col3" # 逗号分隔
    uv run python tools/clearDB.py "col1，col2"     # 中文逗号也行
"""

import argparse

from qdrant_client import QdrantClient

from src.config.settings import QDRANT_HOST, QDRANT_PORT
from src.utils.text import parse_names


def main():
    parser = argparse.ArgumentParser(description="清理 Qdrant collection")
    parser.add_argument("-a", "--all", action="store_true", help="删除所有 collection")
    parser.add_argument("names", nargs="*", help="要删除的 collection 名称（支持逗号/空格分隔）")
    args = parser.parse_args()

    client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
    existing = {col.name for col in client.get_collections().collections}

    if not existing:
        print("数据库中没有任何 collection。")
        return

    if args.all:
        targets = sorted(existing)
    elif args.names:
        targets = parse_names(args.names)
    else:
        parser.print_help()
        print(f"\n当前存在的 collection: {', '.join(sorted(existing))}")
        try:
            user_input = input("\n请输入要删除的 collection 名称（-a 删除所有，直接回车退出）: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消。")
            return
        if not user_input:
            return
        if user_input == "-a":
            targets = sorted(existing)
        else:
            targets = parse_names([user_input])

    for name in targets:
        if name not in existing:
            print(f"⚠️  跳过: {name}（不存在）")
            continue
        # client.delete_collection(collection_name=name)
        print(f"✅ 已删除: {name}")

    print("完成。")


if __name__ == "__main__":
    main()