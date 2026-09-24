import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ============ 两个真实函数（内容完全一样，只是名字不同）============
def weather_tool(latitude, longitude):
    return f"[WEATHER] 杭州 30.1°C 5.4 m/s (lat={latitude}, lng={longitude})"

def time_tool(latitude, longitude):
    return f"[TIME] 现在北京时间 15:42 (lat={latitude}, lng={longitude})"


def run_experiment(name, tools, question):
    print("=" * 60)
    print(f"实验 {name}")
    print(f"用户问：{question}")
    names = [t["function"]["name"] for t in tools]
    print(f"可用工具：{names}")
    print("-" * 60)

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": question}],
        tools=tools,
    )
    msg = resp.choices[0].message

    if msg.tool_calls:
        for tc in msg.tool_calls:
            print(f"  → 模型调用：{tc.function.name}")
            print(f"  → 参数：{tc.function.arguments}")
    else:
        print(f"  → 模型没调用工具，直接回答：{msg.content}")
    print()


# ================= 实验 A：描述正常 =================
tools_a = [
    {
        "type": "function",
        "function": {
            "name": "weather_tool",
            "description": "查询指定经纬度的当前天气（气温、风速）",
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
            "name": "time_tool",
            "description": "查询指定经纬度所在地的当前时间",
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
]

run_experiment("A：正常描述", tools_a, "杭州现在天气怎么样？")
run_experiment("A2：正常描述", tools_a, "杭州现在几点？")


# ================= 实验 B：描述模糊（改成有语义的参数名） =================
tools_b = [
    {
        "type": "function",
        "function": {
            "name": "weather_tool",
            "description": "查询指定经纬度的当前天气，返回气温和风速",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "纬度，范围 -90 到 90，例如杭州是 30.27"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "经度，范围 -180 到 180，例如杭州是 120.15"
                    },
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "time_tool",
            "description": "查询指定经纬度所在地的当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "纬度，范围 -90 到 90，例如杭州是 30.27"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "经度，范围 -180 到 180，例如杭州是 120.15"
                    },
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
]

run_experiment("B（修改后）：语义清晰", tools_b, "杭州现在天气怎么样？")

# ================= 实验 C：描述矛盾（功能说反） =================
tools_c = [
    {
        "type": "function",
        "function": {
            "name": "weather_tool",
            "description": "查询指定经纬度所在地的当前时间",
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
            "name": "time_tool",
            "description": "查询指定经纬度的当前天气",
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
]

run_experiment("C：描述矛盾", tools_c, "杭州现在天气怎么样？")
run_experiment("B（修改后）：语义清晰", tools_b, "北京现在天气怎么样？")