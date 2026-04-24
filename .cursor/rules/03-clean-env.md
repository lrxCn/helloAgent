# Rule 03: 环境洁癖与依赖管理 (Clean Environment)

## 核心职责
- **uv 优先**: 所有的 Python 依赖安装、脚本运行必须优先使用 `uv` 体系（`uv run`, `uv pip`）。
- **Git 纯净**: 任何新生成的本地持久化文件、缓存文件、日志备份，必须第一时间同步更新到 `.gitignore` 中。

## 绝对原则
严禁将本地测试产生的垃圾文件（如 .venv2, logs_old, trace.log）留在仓库中或提交到远端。
