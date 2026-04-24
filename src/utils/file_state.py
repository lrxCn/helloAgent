import json
import logging
from pathlib import Path

from config.settings import SYNC_STATE_FILE_NAME

logger = logging.getLogger(__name__)

class FileStateManager:
    """管理文件级修改时间 (mtime) 的本地缓存状态。"""

    def __init__(self, data_dir: Path):
        self.state_file = Path(data_dir) / SYNC_STATE_FILE_NAME

    def load(self) -> dict:
        """从本地加载之前的同步状态。"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取同步状态失败，将重新全量加载: {e}")
        return {}

    def save(self, state: dict):
        """将最新的同步状态保存到本地。"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存同步状态失败: {e}")
