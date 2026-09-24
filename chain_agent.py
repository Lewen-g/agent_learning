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

def geocode(city: str) -> str:
    """把城市名转换成经纬度（用 Open-Meteo 的 geocoding API）"""
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "zh"},
        timeout=10,
    )
    data = r.json()
    results = data.get("results")
    if not results:
        return f"找不到城市：{city}"
    item = results[0]
    lat = item["latitude"]
    lng = item["longitude"]
    name = item.get("name", city)
    country = item.get("country", "")
    return f"{name}（{country}）的坐标是 latitude={lat}, longitude={lng}"


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
            "name": "geocode",
            "description": "把城市名转换为经纬度坐标。当需要某个城市的坐标时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名，中文或英文，例如 '杭州' 或 'Hangzhou'"
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定经纬度所在地的当前天气。需要用坐标查询，不能直接用城市名。",
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
                    "expression": {
                        "type": "string",
                        "description": "数学表达式字符串，如 '123 * 456'"
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


# ==================== 3. 工具名 → 函数映射 ====================

TOOL_MAP = {
    "geocode": geocode,
    "get_weather": get_weather,
    "calculator": calculator,
}


# ==================== 4. Agent Loop（核心） ====================

def ask(question: str, max_steps: int = 10):
    print("=" * 60)
    print(f"❓ 你问：{question}")

    messages = [{"role": "user", "content": question}]

    for step in range(max_steps):
        # 调模型
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        msg = resp.choices[0].message
        messages.append(msg)

        # 模型不再请求工具 → 结束
        if not msg.tool_calls:
            print(f"✅ 最终回答：{msg.content}")
            print(f"   （共 {step + 1} 轮）")
            print()
            return

        # 执行所有工具调用
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"🔧 第 {step + 1} 轮调用：{name}({args})")

            if name in TOOL_MAP:
                result = TOOL_MAP[name](**args)
            else:
                result = f"未知工具：{name}"

            print(f"📦 返回：{result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    print("⚠️ 达到最大步数，停止")
    print()


# ==================== 5. 测试 ====================

if __name__ == "__main__":
    ask("杭州现在天气怎么样？")
    ask("北京和上海哪里更热？")
    ask("杭州现在气温是多少度？把它乘以 2 是多少？")