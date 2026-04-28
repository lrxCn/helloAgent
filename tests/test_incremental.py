import sys
import os
import time
import shutil
import unittest
from pathlib import Path

# 确保能引入 src 下的模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.loader import load_all_docs

class TestIncrementalSync(unittest.TestCase):
    def setUp(self):
        """测试前准备临时目录"""
        self.test_data_dir = PROJECT_ROOT / "tests" / "test_data"
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.file1 = self.test_data_dir / "doc1.txt"

    def tearDown(self):
        """测试后清理临时目录"""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)

    def test_file_level_mtime_interception(self):
        """测试第一层防线：基于 mtime 的本地文件加载拦截"""
        # 1. 写入测试文件
        self.file1.write_text("Hello World", encoding="utf-8")
        
        # 2. 第一次加载（应全部切分）
        chunks1 = load_all_docs(self.test_data_dir)
        self.assertGreater(len(chunks1), 0, "第一次加载应当产生 chunk")

        # breakpoint()
        
        # 3. 第二次加载（不修改文件，应被 mtime 拦截）
        chunks2 = load_all_docs(self.test_data_dir)
        self.assertEqual(len(chunks2), 0, "未修改时应当被直接拦截，返回空列表")
        # breakpoint()
        
        # 4. 第三次加载（修改文件，应重新切分）
        time.sleep(1) # 睡眠以确保系统 mtime 会更新
        self.file1.write_text("Hello World Updated", encoding="utf-8")
        chunks3 = load_all_docs(self.test_data_dir)
        self.assertGreater(len(chunks3), 0, "文件被修改后，应当产生新的 chunk")
        # breakpoint()


if __name__ == "__main__":
    unittest.main(verbosity=2)
