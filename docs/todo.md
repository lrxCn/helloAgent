# 项目优化清单 (TODO)


## 待精简与重构的部分 (Refactoring & Streamlining)

在审视当前代码架构后，以下部分显得有些冗余或不够“优雅”，建议在后续版本中精简和重构：

### 1. 废弃代码清理
- [x] **清理硬编码测试**：`src/main.py` 底部保留了大段被注释掉的旧版测试代码（`_test_vectorstore` 等），既然核心流程已经跑通，这些历史遗留代码应当彻底删除，保持入口文件清爽。

### 2. LangChain 链的规范化（去除手动拼接）
- [x] **问题**：在 `src/core/chat.py` 的 `answer` 方法中，目前是使用原生的 Python 字符串操作（`context_parts.append` 和 `join`）来拼接参考资料。
- [x] **优化**：这种硬编码方式不够灵活。建议使用 LangChain 原生的 `create_stuff_documents_chain`，将上下文变量直接丢给 Prompt Template 处理。这样不仅代码更少，更换提示词模板时也更方便。

### 3. Rerank 逻辑封装 (ContextualCompressionRetriever)
- [x] **问题**：目前检索逻辑是分为两步走的，先从 DAO 取回数据，再手动传给 `reranker.py` 去做精排。外部调用者（`chat.py`）需要关心重排的细节。
- [x] **优化**：利用 LangChain 的 `ContextualCompressionRetriever`，把基础的 VectorStore Retriever 和自定义的 BGE Reranker（包装成 `BaseDocumentCompressor`）合二为一。这样在主逻辑中，只需简单调用 `retriever.invoke(query)` 就能自动完成“粗排+精排”的整套流水线。

### 4. 依赖实例的复用
- [x] **问题**：目前如果有多个地方需要交互，或者重复实例化 `SmartAgent`，都会重新初始化 `ChatOpenAI` 和 `get_dao()` 连接。
- [x] **优化**：随着应用变大，可以将大模型实例和数据库连接实例抽象为单例（Singleton）或在 `main.py` 初始化时作为依赖注入（Dependency Injection），避免建立重复的网络连接。

### 5. 引入 LangSmith
- [x] **装 LangSmith**：集成 LangSmith 以便更好地监控、调试和评估 Agent 运行状态。
