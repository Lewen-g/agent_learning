import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ==================== 1. 真实工具函数 ====================

def get_weather(latitude: float, longitude: float) -> str:
    """查指定经纬度的天气"""
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m",
        },
        timeout=10,
    )
    c = r.json().get("current", {})
    temp = c.get("temperature_2m")
    wind = c.get("wind_speed_10m")
    if temp is None:
        return "天气数据不可用"
    return f"当前气温 {temp}°C，风速 {wind} m/s。"


def calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        # ⚠️ 学习用，真实项目绝不要用 eval，要用 ast.literal_eval 或专门库
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return f"不支持的表达式：{expression}"
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算出错：{e}"


# ==================== 2. 工具说明书 ====================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定经纬度所在地的当前天气，返回气温和风速。仅当用户询问天气时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "纬度，范围 -90 到 90。例如杭州 30.27"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "经度，范围 -180 到 180。例如杭州 120.15"
                    },
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，支持加减乘除和括号。仅当用户明确要求做数学计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式字符串，例如 '123 * 456' 或 '(3 + 5) * 2'"
                    },
                },
                "required": ["expression"],
            },
        },
    },
]


# ==================== 3. 工具名 → 函数 的映射 ====================

TOOL_MAP = {
    "get_weather": get_weather,
    "calculator": calculator,
}


# ==================== 4. 单个问题跑一次 Agent ====================

def ask(question: str):
    print("=" * 60)
    print(f"❓ 你问：{question}")

    messages = [{"role": "user", "content": question}]

    # 第一轮：让模型决定
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
    )
    msg = resp.choices[0].message
    messages.append(msg)

    if not msg.tool_calls:
        print(f"💬 模型直接回答：{msg.content}")
        print()
        return

    # 有工具调用：逐个执行
    for tc in msg.tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments)
        print(f"🔧 模型调用：{name}({args})")

        if name in TOOL_MAP:
            result = TOOL_MAP[name](**args)
        else:
            result = f"未知工具：{name}"

        print(f"📦 工具返回：{result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": str(result),
        })

    # 第二轮：让模型总结
    final = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
    )
    print(f"✅ 最终回答：{final.choices[0].message.content}")
    print()


# ==================== 5. 测试 ====================

if __name__ == "__main__":
    ask("杭州现在天气怎么样？")
    ask("123 * 456 等于多少？")
    ask("(3 + 5) * 2 - 10 是多少？")
    ask("杭州天气怎么样？顺便帮我算一下 88 * 99")
    ask("你是谁？")