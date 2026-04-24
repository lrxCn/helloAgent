# Changelog

所有对 helloAgent 项目的重大修改都会记录在这个文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [Unreleased] (本次更新)

### ✨ 新增 (Added)
- **增量去重机制（第一道防线）**：在 `src/core/loader.py` 中引入基于 `mtime` 的文件级拦截，配合 `.sync_state.json` 避免未修改的文档发生重复切分，降低本地 CPU 消耗。
- **架构解耦设计**：在 `src/dao/__init__.py` 中新增 `get_record_manager` 工厂方法，剥离了具体的 SQLite 实现逻辑，为未来支持 Redis/PostgreSQL 提供便利。
- **系统架构图**：在 `README.md` 中引入 Mermaid 绘制的 RAG 架构流程图，直观展示启动、加载和问答的处理流水线。
- **自动化测试用例**：在 `tests/test_incremental.py` 中新增了基于 `unittest` 的单元测试，用于验证基于 `mtime` 的增量加载和拦截防线是否可靠。
- **长期演进规划**：在 `docs/prd.md` 中增加了“工业级架构演进方向”（涵盖事件驱动异步架构、智能文档提取、多租户向量隔离等）。
- **重构任务清单**：新增 `docs/todo.md`，记录后续的代码清理、LangChain Chain 规范化及 `ContextualCompressionRetriever` 的封装计划。

### ♻️ 重构 (Refactored)
- **拦截逻辑抽离**：将 `loader.py` 中负责文件最后修改时间 (mtime) 的读写拦截逻辑，抽离成了独立的 `utils/file_state.py::FileStateManager` 类，避免业务层代码过度臃肿。
- **硬编码提取**：将 `loader.py` 中硬编码的 `.sync_state.json` 抽取到了全局配置文件 `config/settings.py` 中，作为 `SYNC_STATE_FILE_NAME` 变量统一管理。
- **向量维度获取**：重构 `QdrantDAO`，抽离出 `_get_embedding_dimension` 方法。通过发送测试 query 动态探测当前配置的 Embedding 模型维度，提高系统在切换大模型时的健壮性。
- **向量库同步（第二道防线）**：重构 `src/dao/qdrant_dao.py` 中的 `store_documents` 方法。使用 LangChain 官方的 `SQLRecordManager` + `index` API，实现了精确到段落（Chunk）级别的增量同步，大幅节约 OpenAI API Token 开销。

### 🗑 移除 (Removed)
- 废除了 `store_documents` 中自行编写的文件删除和 MD5 拼接排重逻辑，全面交由 `index` API 接管。

### 🔧 修复 (Fixed)
- 修复了 README Mermaid 流程图中 `subgraph` ID 包含中文导致的渲染报错问题。
- 在 `.gitignore` 中追加忽略 `.sync_state.json` 与 `record_manager_cache.sql` 等本地数据缓存文件，避免污染 Git 仓库。
- 调整并验证了日志自动清理机制，将 `.env` 默认配置中的过期保留时间 `LOG_RETENTION_DAYS` 从 1 天延长为 2 天，并补充了相应的 `tests/test_logger.py` 自动化测试保障。
