# TODO: 下个版本优化文档加载流程

在下个版本中，我们将实施**方案三（LangChain Indexing API / RecordManager）**来优化 `loader.py` 的加载和向量化逻辑。

## 存在的问题
当前在 `src/main.py` 启动时，`loader.py` 中的 `load_all_txt()` 会盲目地将 `data` 目录下的所有 txt 文件全部重新读取和切分。接着，虽然 `QdrantDAO.store_documents` 在插入前会删除旧数据，但仍然会对所有文本块（包括毫无变化的内容）重新调用 OpenAI API 计算 Embedding。
这不仅浪费了本地加载和切分的时间，还**白白消耗了昂贵的 OpenAI API Token 费用**。

## 实施方案三（LangChain Indexing API）
引入 LangChain 原生的 `SQLRecordManager`。它专门用于管理文档索引的同步状态：
1. 会在本地建立一个小型的 SQLite 数据库来记录每个文档（Chunk）的内容哈希。
2. 在更新向量库时，自动识别出哪些文件被修改了、哪些是新增的、哪些被删除了。
3. 只有发生变化的文档块，才会发送给 OpenAI 重新计算 Embedding，从而彻底解决资源和费用的浪费问题。

---

## 待精简与重构的部分 (Refactoring & Streamlining)

在审视当前代码架构后，以下部分显得有些冗余或不够“优雅”，建议在后续版本中精简和重构：

### 1. 废弃代码清理
- **清理硬编码测试**：`src/main.py` 底部保留了大段被注释掉的旧版测试代码（`_test_vectorstore` 等），既然核心流程已经跑通，这些历史遗留代码应当彻底删除，保持入口文件清爽。

### 2. LangChain 链的规范化（去除手动拼接）
- **问题**：在 `src/core/chat.py` 的 `answer` 方法中，目前是使用原生的 Python 字符串操作（`context_parts.append` 和 `join`）来拼接参考资料。
- **优化**：这种硬编码方式不够灵活。建议使用 LangChain 原生的 `create_stuff_documents_chain`，将上下文变量直接丢给 Prompt Template 处理。这样不仅代码更少，更换提示词模板时也更方便。

### 3. Rerank 逻辑封装 (ContextualCompressionRetriever)
- **问题**：目前检索逻辑是分为两步走的，先从 DAO 取回数据，再手动传给 `reranker.py` 去做精排。外部调用者（`chat.py`）需要关心重排的细节。
- **优化**：利用 LangChain 的 `ContextualCompressionRetriever`，把基础的 VectorStore Retriever 和自定义的 BGE Reranker（包装成 `BaseDocumentCompressor`）合二为一。这样在主逻辑中，只需简单调用 `retriever.invoke(query)` 就能自动完成“粗排+精排”的整套流水线。

### 4. 依赖实例的复用
- **问题**：目前如果有多个地方需要交互，或者重复实例化 `SmartAgent`，都会重新初始化 `ChatOpenAI` 和 `get_dao()` 连接。
- **优化**：随着应用变大，可以将大模型实例和数据库连接实例抽象为单例（Singleton）或在 `main.py` 初始化时作为依赖注入（Dependency Injection），避免建立重复的网络连接。
