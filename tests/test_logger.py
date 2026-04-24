import sys
import os
import unittest
import shutil
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.settings import LOG_RETENTION_DAYS
from utils.logger import _cleanup_expired_logs

class TestLogger(unittest.TestCase):
    def setUp(self):
        """准备临时的日志目录"""
        self.test_log_dir = PROJECT_ROOT / "tests" / "test_logs"
        if self.test_log_dir.exists():
            shutil.rmtree(self.test_log_dir)
        self.test_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 临时替换 logger 内部的变量指向测试目录
        from utils import logger
        self.original_log_dir = logger.LOG_DIR
        self.original_retention = logger.LOG_RETENTION_DAYS
        logger.LOG_DIR = self.test_log_dir
        logger.LOG_RETENTION_DAYS = 2

    def tearDown(self):
        from utils import logger
        logger.LOG_DIR = self.original_log_dir
        logger.LOG_RETENTION_DAYS = self.original_retention
        if self.test_log_dir.exists():
            shutil.rmtree(self.test_log_dir)

    def test_cleanup_expired_logs(self):
        """测试清理超过 LOG_RETENTION_DAYS 的日志文件"""
        self.assertEqual(LOG_RETENTION_DAYS, 2, "日志过期时间应该已被配置为 2 天")
        
        today = datetime.now()
        # 创建今天、昨天、3天前的文件
        file_today = self.test_log_dir / f"{today.strftime('%Y-%m-%d')}.log"
        file_yesterday = self.test_log_dir / f"{(today - timedelta(days=1)).strftime('%Y-%m-%d')}.log"
        file_expired = self.test_log_dir / f"{(today - timedelta(days=3)).strftime('%Y-%m-%d')}.log"
        
        file_today.write_text("today")
        file_yesterday.write_text("yesterday")
        file_expired.write_text("expired")
        
        self.assertTrue(file_today.exists())
        self.assertTrue(file_yesterday.exists())
        self.assertTrue(file_expired.exists())
        
        breakpoint()
        # 执行清理
        _cleanup_expired_logs()
        breakpoint()
        
        self.assertTrue(file_today.exists(), "今天的日志不应被删")
        self.assertTrue(file_yesterday.exists(), "昨天的日志不应被删")
        self.assertFalse(file_expired.exists(), "超过2天的日志应该被删除")

if __name__ == "__main__":
    unittest.main(verbosity=2)
