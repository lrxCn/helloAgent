"""项目全局配置，从 .env 文件加载。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── 项目路径 ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
SYNC_STATE_FILE_NAME = os.getenv("SYNC_STATE_FILE_NAME", ".sync_state.json")

# ─── 日志 ───
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "2"))

# ─── 向量数据库 ───
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "qdrant")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# ─── OpenAI / LLM ───
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "")

# ─── Embedding ───
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ─── Rerank ───
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))

# ─── RAG ───
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))           # 最终喂给 LLM 的文档数
RAG_RECALL_K = int(os.getenv("RAG_RECALL_K", "10"))     # 向量检索粗筛数量

# ─── Prompt ───
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "你是一个智能 AI 助手，请用中文简洁清晰地回答用户的问题。\n"
    "当用户的提问中包含【参考资料】时，请你优先基于参考资料进行回答，并在回答中明确指出参考了哪篇文档（来源）。\n"
    "如果参考资料无法完全解答该问题，或者没有提供参考资料，请结合你自身的知识来回答。"
)

# ─── 知识库 ───
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "reading_notes")
