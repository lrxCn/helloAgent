# 📚 AI 读书笔记助手 — 产品需求文档（PRD）

## 1. 项目概述

**产品名称：** helloAgent — AI 读书笔记助手

**一句话描述：** 加载本地文档，AI 帮你总结要点、回答问题、支持多轮追问。

**目标用户：** LangChain 初学者（即作者本人），通过实战项目学习 LangChain 核心概念。

**项目定位：** 学习项目，不追求生产级完善度，重点覆盖 LangChain 关键知识点。

---

## 2. 核心功能

### P0 — 必做

| 编号 | 功能       | 描述                                               |
| ---- | ---------- | -------------------------------------------------- |
| F1   | 文档加载   | 支持加载本地 `.txt` 文件，读取文本内容             |
| F2   | 文档切分   | 将长文档按段落/字数切分为多个小块（chunk）         |
| F3   | 向量化存储 | 将切分后的文档块转为向量，存入 Qdrant 向量数据库   |
| F4   | 智能问答   | 用户输入问题 → 检索相关文档块 → LLM 基于上下文回答 |
| F5   | 多轮对话   | 支持连续追问，AI 记住对话历史                      |

### P1 — 应做

| 编号 | 功能       | 描述                                 |
| ---- | ---------- | ------------------------------------ |
| F6   | 文档摘要   | 一键生成文档的结构化摘要（要点列表） |
| F7   | 多格式支持 | 支持 `.md`、`.pdf` 格式的文档加载    |

### P2 — 可选

| 编号 | 功能       | 描述                             |
| ---- | ---------- | -------------------------------- |
| F8   | Web UI     | 提供简单的网页界面替代命令行交互 |
| F9   | 多文档管理 | 支持加载多份文档，按文档名检索   |

---

## 3. 用户交互流程

```
用户启动程序
    │
    ├─ 选择文档 → 加载并向量化 → 提示"文档已就绪"
    │
    └─ 进入对话模式
         │
         ├─ 输入问题 → AI 检索相关段落 → 生成回答 → 显示回答
         ├─ 输入 /summary → 生成文档摘要
         ├─ 输入 /load <文件路径> → 加载新文档
         └─ 输入 /quit → 退出
```

---

## 4. 非功能性需求

- **响应速度：** 单次问答响应 < 10 秒（取决于 LLM API 速度）
- **配置灵活：** 通过 `.env` 文件配置 LLM 和向量数据库连接
- **代码结构：** 模块化组织，便于学习和理解各组件职责

---

## 5. 学习目标映射

每个功能对应需要掌握的 LangChain 概念：

| 功能          | LangChain 概念                           |
| ------------- | ---------------------------------------- |
| F1 文档加载   | `TextLoader` / `UnstructuredFileLoader`  |
| F2 文档切分   | `RecursiveCharacterTextSplitter`         |
| F3 向量化存储 | `OpenAIEmbeddings` + `QdrantVectorStore` |
| F4 智能问答   | `ChatPromptTemplate` + `RetrievalChain`  |
| F5 多轮对话   | `ConversationBufferMemory`               |
| F6 文档摘要   | `load_summarize_chain`                   |

---

## 6. 开发计划

| 阶段    | 内容                                  | 预计时间 |
| ------- | ------------------------------------- | -------- |
| Phase 1 | 最简 LLM 调用：Prompt + Model + 输出  | 0.5 天   |
| Phase 2 | 文档加载与切分                        | 0.5 天   |
| Phase 3 | RAG 问答：Embedding + Qdrant + 检索链 | 1 天     |
| Phase 4 | 多轮对话记忆                          | 0.5 天   |
| Phase 5 | 文档摘要（可选）                      | 0.5 天   |

---

## 7. 长期规划 (工业级架构演进方向)

虽然本项目定位于小作坊式的本地学习和辅助工具，但随着业务的拓展和需求升级，未来将考虑逐步向工业级架构演进，具体规划如下：

### 7.1 事件驱动与异步架构 (Event-driven Architecture)

- **现状**：每次启动时同步扫描本地目录并阻塞执行全量文档的切分和向量化。
- **演进**：引入消息队列（如 Redis/RabbitMQ/Kafka）和 Webhook。支持用户前端上传文件后，生成异步任务处理文档，后台 Worker 集群按队列消费任务（包括重试、状态追踪、死信队列等），主程序不再被阻塞。

### 7.2 智能文档解析 (Advanced ETL & Parsing)

- **现状**：单纯的 `TextLoader` 处理，强行按字符和换行符切分，不关注原始文档的结构（如段落、表格、图表）。
- **演进**：集成专业非结构化数据解析工具（如 Unstructured.io）。实现基于语义块（Semantic Chunking）的切分，保留层级结构（Heading、Paragraph）、表格数据提取、以及可能的 OCR 图像提取。

#### 实现思路建议：
1. **引入专业解析库 (Unstructured.io)**：
   - 替换现有的单一 `TextLoader`，引入 `UnstructuredFileLoader` 或直接使用 `unstructured` 核心库。
   - 支持解析 PDF、Word、HTML、Markdown 等复杂格式，将文档自动分类为结构化元素（如 `Title`, `NarrativeText`, `Table`, `Image` 等）。
2. **语义化分块 (Semantic Chunking)**：
   - 摒弃单纯依靠字符长度的 `RecursiveCharacterTextSplitter`。
   - 改用基于文档结构的分块策略（例如 Unstructured 的 `chunk_by_title`），将同一个标题下相关的段落合并为一个 Chunk，确保 LLM 检索时能获取完整的语义片段。
3. **元数据 (Metadata) 提取与保留**：
   - 在解析时捕获丰富的上下文 Metadata，包括：文件名、页码、章节层级、上级标题等。
   - 在存入 Qdrant 向量库时，将这些 Metadata 随向量一同写入，以便在检索阶段（Retrieval）支持按 Metadata 进行精准过滤或混合检索（Hybrid Search）。
4. **多模态与复杂元素处理**：
   - **表格提取**：将提取到的表格转换为 HTML 或 Markdown 格式存入，保留行列关系，方便 LLM 进行数据推理。
   - **图像/OCR**：对于扫描版文档或图片，集成 Tesseract 提取文字；对于图表，可借助多模态模型（如 GPT-4o 或 Gemini）预先生成图像摘要（Image Summary），并将摘要文本向量化入库。

### 7.3 多租户向量隔离 (Vector Multi-tenancy & Isolation)

- **现状**：所有文档存放在同一个大 Collection（表）中。
- **演进**：在向量库中通过 Metadata 支持 `tenant_id` 或 `user_id`，在存入和检索时强制附加权限过滤（Filter），实现不同用户知识库的安全隔离，或者为不同租户分配独立的 Collection。

### 7.4 分布式缓存与增量去重 ✅ 已实现

- **现状**：依赖本地 SQLite（`SQLRecordManager`）结合本地文件系统的 `mtime` 完成单机的增量去重。

### 7.5 分层记忆架构 (Multi-layer Memory Architecture) ✅ 已实现

- **现状**：目前计划使用简单的对话缓存（如 `ConversationBufferMemory`），记忆随程序重启丢失，且长对话会导致 Token 消耗激增。
- **演进**：构建“三层记忆模型”，平衡时序逻辑、Token 成本与长效存储：
  1.  **短期上下文 (SQL Layer)**：使用 SQLite/Redis 存储最近 N 轮（如 5-10 轮）的原始对话原文。确保 AI 能够精准理解当下的指代（如“它”、“刚才那个”）和对话时序。
  2.  **中期摘要 (Summary Layer)**：当对话超过窗口上限时，调用 LLM 对最早的几轮对话进行“滚动压缩（Summarization）”。将摘要结果持久化并作为上下文背景，在节省 Token 的同时保留关键意图。
  3.  **长期归档 (Vector Layer)**：将更久远的、被摘要替换掉的原始对话片段进行 Embedding 向量化，存入 Qdrant 的独立集合（如 `user_memories`）。当用户提到很久以前的事情时，通过语义检索按需找回相关细节。

#### 实施步骤建议：

1.  **第一步：持久化存储**。引入 `SQLChatMessageHistory`，将对话记录存入本地 SQLite，实现跨会话记忆。
2.  **第二步：滑动窗口与摘要生成**。实现监控逻辑，当消息数达阈值时，自动提取老旧消息生成 Summary 并更新 Context 模板。
3.  **第三步：记忆向量化沉淀**。将废弃的原始消息归档至向量数据库，配合 `Condense Question` 链实现“记忆召回”。
