# Rule 02: 低耦合架构 (Low Coupling Architecture)

## 核心职责
- 坚决抵制“面条代码”，核心业务逻辑与底层基础设施（DB, Cache, File IO）必须解耦。
- 优先使用 Manager 或 DAO 层封装底层操作，loader 或 chat 等核心流程只通过接口调用。

## 绝对原则
任何基础设施相关的代码（如 JSON 读写、DB 连接）如果出现在业务主流程中超过 5 行，必须考虑抽离到 utils 或相关的管理层。
