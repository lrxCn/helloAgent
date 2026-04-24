"""验证重复数据对向量检索 + Rerank 的影响。"""

from utils.logger import setup_logging
setup_logging()

from core.loader import load_and_split
from core.reranker import rerank
from dao import get_dao

QUERY = "在天愿作什么鸟"
COLLECTION = "test_duplicate"

dao = get_dao()

# ─── 清理 ───
# if dao.collection_exists(COLLECTION):
#     dao.delete_collection(COLLECTION)

# ─── 第一步：存 1 份（正常） ───
chunks = load_and_split("data/sample.txt")
dao.store_documents(chunks, COLLECTION)
print(f"\n{'='*60}")
print(f"📦 存了 1 次，共 {len(chunks)} 条文档")
print(f"{'='*60}")

results = dao.search_with_scores(QUERY, COLLECTION, top_k=5)
print(f"\n🔍 向量检索 top_k=5:")
for i, (doc, score) in enumerate(results):
    preview = doc.page_content.replace("\n", " ")
    print(f"  [{i+1}] 向量分={score:.4f} | {preview}...")

raw_docs = [doc for doc, _ in results]
reranked = rerank(QUERY, raw_docs, top_n=5, threshold=0.0)  # threshold=0 全部显示
print(f"\n🔄 Rerank 结果:")
for i, (doc, score) in enumerate(reranked):
    preview = doc.page_content.replace("\n", " ")
    print(f"  [{i+1}] rerank分={score:.4f} | {preview}...")

# # ─── 第二步：再存 2 次（模拟重复入库） ───
# dao.store_documents(chunks, COLLECTION)
# dao.store_documents(chunks, COLLECTION)
# print(f"\n\n{'='*60}")
# print(f"📦 又存了 2 次，现在共 {len(chunks) * 3} 条文档（含重复）")
# print(f"{'='*60}")

# # top_k=3 的情况
# results_3 = dao.search_with_scores(QUERY, COLLECTION, top_k=3)
# print(f"\n🔍 向量检索 top_k=3:")
# for i, (doc, score) in enumerate(results_3):
#     preview = doc.page_content[:60].replace("\n", " ")
#     print(f"  [{i+1}] 向量分={score:.4f} | {preview}...")

# raw_docs_3 = [doc for doc, _ in results_3]
# reranked_3 = rerank(QUERY, raw_docs_3, top_n=3, threshold=0.0)
# print(f"\n🔄 Rerank 结果 (top_k=3 的候选):")
# for i, (doc, score) in enumerate(reranked_3):
#     preview = doc.page_content[:60].replace("\n", " ")
#     print(f"  [{i+1}] rerank分={score:.4f} | {preview}...")

# # top_k=10 的情况
# results_10 = dao.search_with_scores(QUERY, COLLECTION, top_k=10)
# print(f"\n🔍 向量检索 top_k=10:")
# for i, (doc, score) in enumerate(results_10):
#     preview = doc.page_content[:60].replace("\n", " ")
#     print(f"  [{i+1}] 向量分={score:.4f} | {preview}...")

# raw_docs_10 = [doc for doc, _ in results_10]
# reranked_10 = rerank(QUERY, raw_docs_10, top_n=10, threshold=0.0)
# print(f"\n🔄 Rerank 结果 (top_k=10 的候选):")
# for i, (doc, score) in enumerate(reranked_10):
#     preview = doc.page_content[:60].replace("\n", " ")
#     print(f"  [{i+1}] rerank分={score:.4f} | {preview}...")

# # ─── 清理测试数据 ───
# dao.delete_collection(COLLECTION)
# print(f"\n🗑️  测试集合已清理")
