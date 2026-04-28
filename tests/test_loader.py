import sys
import shutil
import unittest
from pathlib import Path

# 确保能引入 src 下的模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.loader import load_and_split, load_all_docs


class TestLoader(unittest.TestCase):
    def setUp(self):
        """测试前准备临时目录和测试文件"""
        self.test_data_dir = PROJECT_ROOT / "tests" / "test_loader_data"
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.md_file = self.test_data_dir / "test_doc.md"
        self.txt_file = self.test_data_dir / "test_doc2.txt"

    def tearDown(self):
        """测试后清理临时目录"""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)

    def test_load_and_split_markdown(self):
        """测试单个 Markdown 文件的加载与语义切分"""
        content = """# First Title
This is the first paragraph under the first title.

# Second Title
This is the second paragraph under the second title. It should be split into a separate chunk.
"""
        self.md_file.write_text(content, encoding="utf-8")
        
        # 运行加载器
        chunks = load_and_split(str(self.md_file))
        
        # 验证结果
        self.assertGreater(len(chunks), 0, "应当至少生成一个 chunk")
        
        # 验证每个 chunk 是否包含了 metadata
        print("\n" + "="*50)
        print(f"【原文内容】:\n{content}")
        print("-" * 50)
        print(f"【Chunks 切分结果 (共 {len(chunks)} 块)】:")
        for idx, c in enumerate(chunks):
            print(f"  [Chunk {idx}] Metadata: {c.metadata}")
            print(f"  [Chunk {idx}] Content : {c.page_content!r}\n")
            self.assertIsNotNone(c.metadata, "Metadata 不应为空")
            self.assertIn("source", c.metadata, "Metadata 应包含 source 字段")
        print("="*50 + "\n")

    def test_load_all_docs(self):
        """测试批量加载多种格式文件"""
        self.md_file.write_text("# Doc 1", encoding="utf-8")
        self.txt_file.write_text("Doc 2 content", encoding="utf-8")
        
        # 运行批量加载器
        chunks = load_all_docs(self.test_data_dir)
        
        # 验证结果
        self.assertGreaterEqual(len(chunks), 2, "应当加载到两个文件的内容")
        
        # 收集所有 chunk 的来源文件
        print("\n" + "="*50)
        print("【批量加载原始文件】:")
        print(f"  test_doc.md: '# Doc 1'")
        print(f"  test_doc2.txt: 'Doc 2 content'")
        print("-" * 50)
        print(f"【批量 Chunks 切分结果 (共 {len(chunks)} 块)】:")
        sources = []
        for idx, c in enumerate(chunks):
            source = Path(c.metadata["source"]).name
            sources.append(source)
            print(f"  [Chunk {idx} | 来源: {source}] Content : {c.page_content!r}")
        print("="*50 + "\n")
        
        self.assertIn("test_doc.md", sources, "应当包含 md 文件")
        self.assertIn("test_doc2.txt", sources, "应当包含 txt 文件")


if __name__ == "__main__":
    unittest.main(verbosity=2)
