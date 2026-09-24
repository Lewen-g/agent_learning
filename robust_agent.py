import os
import json
import ast
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ==================== 0. 常量表 ====================

# 省份/自治区/直辖市（会骗过 geocoding API）
PROVINCES = {
    "北京", "上海", "天津", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "香港", "澳门",
}

# 本地坐标兜底（API 挂了也能跑）
LOCAL_COORDS = {
    "杭州": (30.27, 120.15),
    "北京": (39.90, 116.40),
    "上海": (31.23, 121.47),
    "广州": (23.13, 113.26),
    "深圳": (22.54, 114.06),
    "成都": (30.57, 104.07),
    "重庆": (29.56, 106.55),
    "南京": (32.06, 118.80),
    "武汉": (30.59, 114.31),
    "西安": (34.34, 108.94),
    "郑州": (34.75, 113.63),
    "哈尔滨": (45.80, 126.53),
    "沈阳": (41.80, 123.43),
    "长沙": (28.23, 112.94),
    "青岛": (36.07, 120.38),
    "厦门": (24.48, 118.09),
    "昆明": (24.88, 102.83),
    "兰州": (36.06, 103.83),
    "乌鲁木齐": (43.83, 87.62),
    "拉萨": (29.65, 91.13),
}


# ==================== 1. 工具函数（都加了校验） ====================

def geocode(city: str) -> str:
    """城市名 → 经纬度。带省份拦截 + API + 本地字典三道防线。"""
    # 防线 1：省份拦截
    if not city or not isinstance(city, str):
        return "错误：城市名不能为空"
    city = city.strip()

    # 去掉可能的"市"后缀做匹配
    city_clean = city.rstrip("市")

    if city_clean in PROVINCES:
        return f"错误：'{city}' 是省级行政区，请提供具体城市名（如'郑州'、'海口'）"

    # 防线 2：API 查询
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=8,
        )
        results = r.json().get("results")
        if results:
            item = results[0]
            lat, lng = item["latitude"], item["longitude"]
            # 校验返回的坐标是否合法
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return f"{city} 的坐标是 latitude={lat}, longitude={lng}"
    except Exception:
        pass  # 网络挂了，走防线 3

    # 防线 3：本地字典
    if city_clean in LOCAL_COORDS:
        lat, lng = LOCAL_COORDS[city_clean]
        return f"{city} 的坐标是 latitude={lat}, longitude={lng}"

    return f"错误：找不到城市'{city}'"


def get_weather(latitude, longitude) -> str:
    """查天气。带坐标范围校验。"""
    # 防线：坐标合法性
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError):
        return "错误：经纬度必须是数字"

    if not (-90 <= lat <= 90):
        return f"错误：纬度 {lat} 超出范围 -90~90"
    if not (-180 <= lng <= 180):
        return f"错误：经度 {lng} 超出范围 -180~180"

    # 请求
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m,wind_speed_10m",
            },
            timeout=8,
        )
        c = r.json().get("current", {})
        temp = c.get("temperature_2m")
        wind = c.get("wind_speed_10m")
        if temp is None:
            return "错误：天气服务未返回数据"
        return f"当前气温 {temp}°C，风速 {wind} m/s。"
    except Exception as e:
        return f"错误：查询天气失败（{type(e).__name__}）"


# 安全计算器：用 AST 白名单，不用 eval
ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ALLOWED_BINOPS):
        return _apply(node.op, _safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ALLOWED_UNARYOPS):
        return _apply(node.op, _safe_eval(node.operand))
    raise ValueError(f"不允许的语法：{type(node).__name__}")


def _apply(op, a, b):
    if isinstance(op, ast.Add): return a + b
    if isinstance(op, ast.Sub): return a - b
    if isinstance(op, ast.Mult): return a * b
    if isinstance(op, ast.Div): return a / b
    if isinstance(op, ast.Pow): return a ** b
    if isinstance(op, ast.Mod): return a % b
    if isinstance(op, ast.UAdd): return +a
    if isinstance(op, ast.USub): return -a
    raise ValueError("不允许的运算")


def calculator(expression: str) -> str:
    """安全计算器：AST 解析，禁 eval。"""
    if not expression or len(expression) > 200:
        return "错误：表达式为空或过长"
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        # 避免结果过大
        if isinstance(result, float) and (abs(result) > 1e12 or result != result):
            return "错误：结果超出安全范围"
        return f"{expression} = {result}"
    except Exception as e:
        return f"错误：计算出错（{type(e).__name__}: {e}）"


# ==================== 2. 工具说明书 ====================

tools = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": (
                "把城市名转换为经纬度坐标。"
                "只支持具体城市，不支持省份（如'河南'、'海南'都不行，需要'郑州'、'海口'）。"
                "建议传英文名（Zhengzhou、Harbin），中文可能查不到。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 'Zhengzhou'"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定经纬度所在地的当前天气。",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "纬度，-90~90"},
                    "longitude": {"type": "number", "description": "经度，-180~180"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，支持 + - * / ** % 和括号。",
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


# ==================== 3. 会话状态 ====================

SYSTEM_PROMPT = """你是一个天气和计算助理。

能力范围：
1. 查询任意城市的天气
2. 做数学计算

规则：
- 只回答天气、地理、数学相关问题；其他领域礼貌拒绝
- 遇到省份、地区名，先追问具体城市
- 涉及精确计算必须调用 calculator，禁止心算
- 回答简短

如果工具返回"错误：..."，说明参数有问题，你可以尝试修正后重试一次；仍失败就如实告诉用户。
"""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
MAX_HISTORY = 20


def trim_history():
    global conversation
    if len(conversation) <= MAX_HISTORY + 1:
        return
    system_msg = conversation[0]
    rest = conversation[1:]
    kept = rest[-MAX_HISTORY:]
    while kept and kept[0].get("role") == "tool":
        kept.pop(0)
    conversation = [system_msg] + kept


# ==================== 4. Agent Loop（加异常兜底） ====================

def call_tool_safe(name: str, args: dict) -> str:
    """安全执行工具：拦所有异常 + 截断超长返回。"""
    if name not in TOOL_MAP:
        return f"错误：未知工具 {name}"
    try:
        result = TOOL_MAP[name](**args)
    except TypeError as e:
        return f"错误：参数不匹配（{e}）"
    except Exception as e:
        return f"错误：工具执行异常（{type(e).__name__}: {e}）"

    result = str(result)
    if len(result) > 500:
        result = result[:500] + "…（已截断）"
    return result


def chat(question: str, max_steps: int = 8):
    global conversation

    print(f"\n👤 你：{question}")
    conversation.append({"role": "user", "content": question})

    for step in range(max_steps):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=conversation,
                tools=tools,
            )
        except Exception as e:
            print(f"🤖 它：模型调用失败（{type(e).__name__}: {e}）")
            return

        msg = resp.choices[0].message
        conversation.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            print(f"🤖 它：{msg.content}")
            trim_history()
            return

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            print(f"   🔧 {name}({args})")

            result = call_tool_safe(name, args)
            print(f"      ↳ {result}")

            conversation.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    print("🤖 它：达到最大步数，无法完成。")
    trim_history()


# ==================== 5. 交互 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("健壮的 Agent 已启动。输入 'exit' 退出。")
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