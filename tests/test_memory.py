import sys
import os
from pathlib import Path

# 将 src 目录加入 path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.memory import MultiLayerMemory
from langchain_core.messages import HumanMessage, AIMessage
from config.settings import MEMORY_WINDOW_SIZE
import logging

# 配置日志以便观察归档过程
logging.basicConfig(level=logging.INFO)

def test_multilayer_memory():
    # 使用随机 session_id 避免干扰现有数据
    import uuid
    session_id = f"test_session_{uuid.uuid4().hex[:6]}"
    print(f"🚀 开始分层记忆测试，Session ID: {session_id}")
    
    memory = MultiLayerMemory(session_id=session_id)
    
    # 1. 测试基础添加
    print("\n--- 步骤 1: 添加初始消息 ---")
    memory.add_message(HumanMessage(content="你好，我是一个专门用来测试分层记忆的机器人。"))
    memory.add_message(AIMessage(content="收到！我会尝试记录我们的对话。"))
    
    msgs = memory.get_short_term_messages()
    print(f"当前短期记忆消息数: {len(msgs)}")
    assert len(msgs) == 2
    
    # 2. 连续添加消息直到触发归档
    # 阈值是 MEMORY_WINDOW_SIZE * 2 (默认 10 * 2 = 20)
    print(f"\n--- 步骤 2: 填充消息触发归档 (窗口大小: {MEMORY_WINDOW_SIZE}) ---")
    # 我们添加比窗口多 2 对的消息
    for i in range(MEMORY_WINDOW_SIZE + 2):
        memory.add_message(HumanMessage(content=f"问题序号 {i}: 今天的第 {i} 个测试点"))
        memory.add_message(AIMessage(content=f"回答序号 {i}: 记录成功，这是针对点 {i} 的反馈"))
    
    # 3. 检查短期记忆是否已截断
    msgs_after = memory.get_short_term_messages()
    print(f"归档后短期记忆(SQL)消息数: {len(msgs_after)}")
    # 应该正好等于 max_messages (MEMORY_WINDOW_SIZE * 2)
    assert len(msgs_after) == MEMORY_WINDOW_SIZE * 2
    
    # 4. 检查中期摘要
    print("\n--- 步骤 3: 检查中期摘要 (Summary Layer) ---")
    summary = memory.get_mid_term_summary()
    print(f"生成的摘要内容: \n{summary}")
    assert len(summary) > 0
    assert "测试" in summary or "记录" in summary
    
    # 5. 检查长期记忆检索
    print("\n--- 步骤 4: 检查长期记忆检索 (Vector Layer) ---")
    # 检索最早被归档的那条消息
    search_query = "专门用来测试分层记忆的机器人"
    long_term_results = memory.get_long_term_memories(search_query)
    print(f"长期记忆检索结果 (针对 '{search_query}'):\n{long_term_results}")
    
    assert len(long_term_results) > 0
    assert "测试用户" in long_term_results or "测试" in long_term_results or "机器人" in long_term_results
    
    print("\n✅ 分层记忆架构(SQL/Summary/Vector)自测成功！")

if __name__ == "__main__":
    try:
        test_multilayer_memory()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
