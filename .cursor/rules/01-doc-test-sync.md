# Rule 01: 文档与测试同步 (Doc & Test Sync)

## 核心职责

在任何功能开发、重构或修复完成后，必须主动完成以下同步：

1. **CHANGELOG.md**: 记录变动（Added, Refactored, Fixed, Removed）。
2. **docs/todo.md**: 更新待办事项，记录技术债。
3. **docs/prd.md**: 同步逻辑变更与长期规划。
4. **测试脚本**: 编写或更新对应的自动化测试用例，并确保跑通。

## 绝对原则

代码 (Code)、测试 (Test) 与文档 (Doc) 同等重要。不完整交付视为不合格。
