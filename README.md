# helloAgent

1. 启动agent
   1. 准备dao
      1. 准备数据库
      2. 准备embeddings，for rerank
   2. 配置systemPrompt，预留user_prompt
   3. 输出 output_parsers
2. 加载rag
   1. data目录下chunk
   2. dataManage
      1. 同source：更新
      2. chunk做md5
      3. 如果表不存在创建表
         1. 通过1个query获取表维度
         2. 根据维度创建表格
      4. 根据md5做差异化，存入表
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

    P3 --> R1
    
    subgraph Phase2 [二、加载 RAG 数据]
        R1[扫描 data 目录执行 Chunk] --> R2[Data Manage]
        R2 --> R2_1(同 source：准备更新)
        R2_1 --> R2_2(对各个 Chunk 计算 MD5)
        R2_2 --> R3{判断表是否存在?}
        
        R3 -->|不存在| R3_1(通过1个query获取表维度)
        R3_1 --> R3_2(根据维度动态创建表格)
        R3_2 --> R4
        
        R3 -->|已存在| R4(根据 MD5 进行差异化对比)
        R4 --> R5[(将新增或差异数据存入表)]
    end

    R5 --> C1
    
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
