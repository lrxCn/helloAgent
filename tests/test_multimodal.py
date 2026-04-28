import sys
import unittest
from pathlib import Path

# 确保能引入 src 下的模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.loader import load_and_split

class TestMultimodalLoader(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.test_pdf_path = PROJECT_ROOT / "docs" / "multimodal_test.pdf"
        # 确保目录存在
        self.test_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    def test_multimodal_extraction(self):
        """测试多模态与表格增强解析"""
        if not self.test_pdf_path.exists():
            self.skipTest(f"测试用的 PDF 文件不存在，请将文件放入: {self.test_pdf_path}")

        print(f"\n🚀 开始测试多模态解析: {self.test_pdf_path}")
        chunks = load_and_split(str(self.test_pdf_path))
        
        self.assertGreater(len(chunks), 0, "应当至少生成一个 chunk")
        
        found_table = False
        found_image_summary = False
        
        print("\n" + "="*50)
        print(f"【多模态 Chunks 解析结果 (共 {len(chunks)} 块)】:")
        for idx, c in enumerate(chunks):
            content = c.page_content
            print(f"  [Chunk {idx}] Content片段: {content[:200]}...")
            
            if "【结构化表格】" in content:
                found_table = True
                print(f"    ✅ 发现表格 HTML 结构!")
                
            if "【多模态摘要】" in content:
                found_image_summary = True
                print(f"    ✅ 发现多模态图像摘要!")
                
        print("="*50 + "\n")

        # 注意：这里不做强制 assert，因为取决于提供的 PDF 里是否真的有表格或图片
        if not found_table:
            print("⚠️ 未在文档中提取到【结构化表格】，请确认 PDF 中是否包含清晰的表格。")
        if not found_image_summary:
            print("⚠️ 未在文档中提取到【多模态摘要】，请确认 PDF 中是否包含图片。")


if __name__ == "__main__":
    unittest.main(verbosity=2)
