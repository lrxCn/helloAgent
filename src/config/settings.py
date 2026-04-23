"""项目全局配置，从 .env 文件加载。"""

import os

from dotenv import load_dotenv

load_dotenv()

# ─── Qdrant ───
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# ─── OpenAI / LLM ───
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
