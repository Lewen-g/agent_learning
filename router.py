import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 两个专职 Agent 作为模块导入
import weather_agent
import app_agent


# ==================== 路由决策 ====================

ROUTER_PROMPT = """你是一个意图分类器。

用户会向你提出请求，你需要判断这个请求属于以下哪一类：

1. weather —— 查询天气、查询地理位置、数学计算、单位换算等
   例子：杭州天气、北京气温、2+3等于多少、100美元是多少人民币

2. app —— 启动电脑上的软件
   例子：打开记事本、启动微信、帮我开一下b站

3. app_pending —— 用户正在回应一个"待确认的软件启动请求"
   例子：确认、取消、好、算了、不要

4. unknown —— 不属于以上任何一类

要求：
- 只输出类别名，不要输出其他文字
- 如果有歧义，选最可能的那个
"""


def route(question: str, has_pending: bool) -> str:
    """用 LLM 判断意图，返回 'weather' / 'app' / 'unknown'"""
    # 如果当前有待确认的操作，优先路由到 app
    if has_pending:
        return "app"

    messages = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": question},
    ]

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        max_tokens=10,      # 只要一个类别名
        temperature=0,      # 别搞创意
    )

    intent = resp.choices[0].message.content.strip().lower()

    # 归一化
    if "weather" in intent:
        return "weather"
    if "app" in intent:
        return "app"
    return "unknown"


# ==================== 主循环 ====================

def main():
    print("=" * 60)
    print("总 Agent 已启动。支持：天气 / 计算 / 启动软件")
    print("输入 'exit' 退出。")
    print("=" * 60)

    while True:
        try:
            question = input("\n👤 你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break

        # 1. 判断意图
        has_pending = app_agent.is_pending()
        intent = route(question, has_pending)
        print(f"   🧭 [路由] {intent}")

        # 2. 交给对应 Agent
        try:
            if intent == "weather":
                answer = weather_agent.handle(question)
            elif intent == "app":
                answer = app_agent.handle(question)
            else:
                answer = "抱歉，我只能帮你查天气、做计算、或启动软件。"
        except Exception as e:
            answer = f"（处理失败：{type(e).__name__}: {e}）"

        print(f"🤖 它：{answer}")


if __name__ == "__main__":
    main()