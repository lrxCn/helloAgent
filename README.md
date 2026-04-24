# helloAgent

1. 启动agent
   1. 准备dao
      1. 准备数据库
      2. 准备embeddings，for rerank
   2. 配置systemPrompt，预留user_prompt
   3. 输出 output_parsers
2. 加载 RAG (双重增量同步模式)
   1. **第一道防线：文件级拦截 (src/core/loader.py)**
      - 扫描 data 目录，通过 `.sync_state.json` 比对文件 `mtime`。
      - 未修改文件直接拦截，避免重复分块，显著降低本地 CPU 消耗。
   2. **第二道防线：索引级同步 (Indexing API)**
      - 初始化 `Record Manager` 持久化文档哈希与同步状态。
      - 自动处理：新增 (Added)、更新 (Updated)、跳过 (Skipped)。
      - 自动清理：清理已从磁盘删除的源文件对应的历史向量。
3. 处理对话与命令
   1. 退出
   2. 异常处理
   3. answer
      1. 带着问题查询向量数据库topN
      2. rerank
      3. 组装
      4. 回答

---

## 系统流程图

```mermaid
graph TD
    Start((程序启动)) --> P1
    
    subgraph Phase1 [一、启动 Agent]
        P1[准备 DAO] --> P1_1(准备数据库连接)
        P1 --> P1_2(准备 Embeddings 用于 Rerank)
        P1_1 --> P2[配置 systemPrompt]
        P1_2 --> P2
        P2 --> P2_1(预留 user_prompt)
        P2_1 --> P3[配置输出 output_parsers]
    end

    P3 --> R0
    
    subgraph Phase2 [二、加载 RAG 数据]
        R0[扫描 data 目录] --> R1{第一道防线: mtime 检查}
        R1 -->|已修改/新文件| R2[执行分块 Chunking]
        R1 -->|未变动| R7[(同步完成)]
        
        R2 --> R3[第二道防线: Indexing Sync]
        R3 --> R4{Indexing API 比对}
        R4 -->|新增/更新| R5[写入向量库并更新记录]
        R4 -->|删除/失效| R6[自动清理旧分块]
        R4 -->|未变动| R7
        R5 --> R7
        R6 --> R7
    end

    R7 --> C1
    
    subgraph Phase3 [三、处理对话与命令]
        C1{接收对话/命令}
        C1 -->|退出| C2([退出程序])
        C1 -->|异常| C3([异常处理])
        
        C1 -->|正常问答| C4_1(带着问题查询向量数据库 TopN)
        C4_1 --> C4_2(Rerank 重排序)
        C4_2 --> C4_3(组装 Prompt 上下文)
        C4_3 --> C4_4(大模型回答)
        C4_4 -.->|循环等待下一轮| C1
    end
```
