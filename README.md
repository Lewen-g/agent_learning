# Agent Learning

![Python](https://img.shields.io/badge/Python-3.13-blue)
![GitHub last commit](https://img.shields.io/github/last-commit/Lewen-g/agent_learning)

从零手写 AI Agent 的学习项目：不用框架，只用 `openai` SDK + Python，
一步步理解 Agent 的底层机制。

## 功能

- **天气查询 Agent**：查任意城市天气，支持链式调用（先查坐标再查天气）
- **计算 Agent**：安全计算数学表达式（基于 AST 白名单，不用 `eval`）
- **软件启动 Agent**：启动电脑上的常用软件（白名单 + 代码层确认机制）
- **多 Agent 路由**：一个入口，按意图自动分发到不同专职 Agent

## 架构

```
router.py                ← 总入口，LLM 路由
├── weather_agent.py     （天气 + 计算，无副作用）
└── app_agent.py         （启动软件，有副作用，带确认状态机）
```

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
.venv\Scripts\activate          # Windows
pip install openai python-dotenv requests
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=sk-你的key
```

> 本项目使用 DeepSeek API（兼容 OpenAI 协议）。
> 去 https://platform.deepseek.com 注册获取 Key。

### 3. 运行

```bash
# 单独运行天气 / 计算 Agent
python weather_agent.py

# 单独运行软件启动 Agent
python app_agent.py

# 运行多 Agent 总入口（推荐）
python router.py
```

## 使用示例

```
👤 你：北京天气
   🧭 [路由] weather
🤖 它：北京当前气温 21.2°C，风速 6.2 m/s。

👤 你：2**100 是多少
   🧭 [路由] weather
🤖 它：2**100 = 1267650600228229401496703205376

👤 你：打开b站
   🧭 [路由] app
🤖 它：我将启动 b站，请回复'确认'以继续，回复'取消'放弃。

👤 你：ok
   🧭 [路由] app
🤖 它：已启动 b站。
```

## 学习路线

1. **环境搭建**：Python venv + `.env` 管理密钥
2. **调用大模型**：`client.chat.completions.create`
3. **第一个工具**：让模型学会调用外部函数
4. **工具契约实验**：理解 description 对模型行为的影响
5. **多工具 Agent**：模型自主选择工具
6. **链式调用**：多步依赖、Agent Loop
7. **多轮记忆**：messages 持久化 + 滑动窗口
8. **鲁棒性加固**：白名单、参数校验、异常兜底
9. **安全确认**：代码层状态机（危险操作先确认）
10. **多 Agent 路由**：LLM 意图分发

## 项目结构

```
agent-learning/
├── .env                  # API Key（不进 Git）
├── .gitignore
├── README.md
├── router.py             # 多 Agent 总入口
├── weather_agent.py      # 天气 + 计算
├── app_agent.py          # 软件启动
└── robust_agent.py       # 学习过程存档（单 Agent 完整版）
```

## 环境要求

- Python 3.11+
- Windows / macOS / Linux
- 可访问 DeepSeek API（国内直连即可）

## License

MIT