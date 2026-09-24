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

# ==================== 工具函数（复用之前的） ====================

def geocode(city: str) -> str:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        )
        results = r.json().get("results")
        if results:
            item = results[0]
            return f"{city} 的坐标是 latitude={item['latitude']}, longitude={item['longitude']}"
    except Exception:
        pass
    known = {"杭州": (30.27, 120.15), "北京": (39.90, 116.40), "上海": (31.23, 121.47)}
    if city in known:
        lat, lng = known[city]
        return f"{city} 的坐标是 latitude={lat}, longitude={lng}"
    return f"找不到城市：{city}"


def get_weather(latitude: float, longitude: float) -> str:
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
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return f"不支持的表达式：{expression}"
        return f"{expression} = {eval(expression)}"
    except Exception as e:
        return f"计算出错：{e}"


# ==================== 工具说明书 ====================

tools = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "把城市名转换为经纬度坐标。当需要某个城市的坐标时。使用城市名请尽量用英文（如 Zhengzhou, Harbin），中文可能查不到。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 '杭州'"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定经纬度所在地的当前天气。需要用坐标查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "纬度"},
                    "longitude": {"type": "number", "description": "经度"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，支持加减乘除和括号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 '123 * 456'"}
                },
                "required": ["expression"],
            },
        },
    },
]

TOOL_MAP = {
    "geocode": geocode,
    "get_weather": get_weather,
    "calculator": calculator,
}


# ==================== 会话状态（核心变化） ====================

SYSTEM_PROMPT = """你是一个天气和计算助理。

你的能力范围：
1. 查询任意城市的天气
2. 做数学计算

规则：
- 只回答与天气、地理、数学相关的问题
- 其他领域问题礼貌拒绝
- 涉及精确计算必须调用 calculator 工具，禁止心算
- 回答简短
"""

# 会话历史（全局变量），第一条永远是 system
conversation = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# 滑动窗口：最多保留多少条非 system 消息
MAX_HISTORY = 4


def trim_history():
    global conversation

    if len(conversation) <= MAX_HISTORY + 1:
        return

    system_msg = conversation[0]
    rest = conversation[1:]

    kept = rest[-MAX_HISTORY:]

    # 规则 1：头部不能是孤立的 tool
    while kept and kept[0].get("role") == "tool":
        kept.pop(0)

    # 规则 2：如果末尾是带 tool_calls 的 assistant 但后面没 tool，删掉它
    #         （实际极少发生，但加了更安全）
    while kept:
        last = kept[-1]
        if last.get("role") == "assistant" and last.get("tool_calls"):
            # 检查它后面的消息里有没有对应的 tool
            has_tool_after = any(
                m.get("role") == "tool" and m.get("tool_call_id") in
                [tc.id for tc in last["tool_calls"]]
                for m in kept
            )
            if not has_tool_after:
                kept.pop()
            else:
                break
        else:
            break

    conversation = [system_msg] + kept


# ==================== Agent Loop（改造后） ====================

def chat(question: str, max_steps: int = 10):
    global conversation

    print(f"\n👤 你：{question}")

    # 把用户消息追加到会话历史
    conversation.append({"role": "user", "content": question})

    # 循环：调模型 → 执行工具 → 喂回，直到模型不再请求工具
    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            tools=tools,
        )
        msg = resp.choices[0].message
        conversation.append(msg.model_dump(exclude_none=True))

        # 没有工具调用 → 这是最终回答
        if not msg.tool_calls:
            print(f"🤖 它：{msg.content}")
            trim_history()
            return msg.content

        # 执行工具调用
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"   🔧 {name}({args})")

            result = TOOL_MAP[name](**args) if name in TOOL_MAP else f"未知工具"

            conversation.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    print("⚠️ 达到最大步数")
    return None


# ==================== 交互式主循环 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Agent 已启动，输入问题开始对话。输入 'exit' 退出。")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n👤 你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break

        chat(user_input)