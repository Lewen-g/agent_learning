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

# ============ 1. 定义真实的工具函数 ============
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
        return "Weather data unavailable."
    return f"当前气温 {temp}°C，风速 {wind} m/s。"

# ============ 2. 告诉模型有哪些工具可用 ============
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location. The user should supply latitude and longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude"},
                    "longitude": {"type": "number", "description": "Longitude"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    }
]

# ============ 3. 第一次调用：模型决定是否调用工具 ============
messages = [
    {"role": "user", "content": "北京现在天气怎么样？"}
]

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
)

message = resp.choices[0].message
messages.append(message)   # 把模型的回复（可能含 tool_calls）加入历史

# ============ 4. 检查模型是否要调用工具 ============
if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"模型想调用: {tool_call.function.name}")
        print(f"参数: {tool_call.function.arguments}")

        args = json.loads(tool_call.function.arguments)

        if tool_call.function.name == "get_weather":
            result = get_weather(args["latitude"], args["longitude"])
        else:
            result = "未知工具"

        print(f"工具返回: {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })

    # ============ 5. 第二次调用：模型用工具结果生成最终回答 ============
    final_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
    )
    print("\n最终回答:")
    print(final_resp.choices[0].message.content)

else:
    print(message.content)