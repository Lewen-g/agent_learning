# Agent Learning

从零手写 AI Agent 的学习项目：不用框架，只用 `openai` SDK + Python，
一步步理解 Agent 的底层机制。

## 功能

- **天气查询 Agent**：查任意城市天气，支持链式调用（先查坐标再查天气）
- **计算 Agent**：安全计算数学表达式（基于 AST 白名单，不用 `eval`）
- **软件启动 Agent**：启动电脑上的常用软件（白名单 + 代码层确认机制）
- **多 Agent 路由**：一个入口，按意图自动分发到不同专职 Agent

## 架构
router.py ← 总入口，LLM 路由
├── weather_agent.py （天气 + 计算，无副作用）
└── app_agent.py （启动软件，有副作用，带确认状态机）


## 核心特性

- ✅ 手写 Agent Loop（不依赖 LangChain）
- ✅ 工具定义（JSON Schema 契约）
- ✅ 链式工具调用（多步依赖）
- ✅ 并行工具调用
- ✅ 多轮对话记忆（滑动窗口）
- ✅ 系统提示词约束（人设 / 边界）
- ✅ 代码层状态机（危险操作先确认）
- ✅ 安全防护（白名单、AST 解析、参数校验、异常兜底）
- ✅ 多 Agent 路由（LLM 意图识别）

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install openai python-dotenv requests