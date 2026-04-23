"""项目全局配置，从 .env 文件加载。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── 项目路径 ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

# ─── 日志 ───
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "1"))

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

# ─── Prompt ───
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "你是一个有帮助的 AI 助手，请用中文回答用户的问题。回答要简洁清晰。",
)
