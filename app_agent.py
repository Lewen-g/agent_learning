import os
import json
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ==================== 1. 白名单（只允许启动这些） ====================

ALLOWED_APPS = {
    "记事本": {
        "exe": "notepad.exe",
        "aliases": ["notepad", "文本编辑器"],
    },
    "计算器": {
        "exe": "calc.exe",
        "aliases": ["calc", "计算"],
    },
    "画图": {
        "exe": "mspaint.exe",
        "aliases": ["mspaint", "paint"],
    },
    "浏览器": {
        "exe": "msedge.exe",
        "aliases": ["edge", "微软浏览器"],
    },
    "资源管理器": {
        "exe": "explorer.exe",
        "aliases": ["文件管理器", "文件夹"],
    },
    "任务管理器": {
        "exe": "taskmgr.exe",
        "aliases": ["task manager"],
    },
    "命令提示符": {
        "exe": "cmd.exe",
        "aliases": ["cmd", "终端"],
    },
    "写字板": {
        "exe": "write.exe",
        "aliases": ["wordpad"],
    },
    "b站": {
        "exe": r"D:\Software\bilibili\哔哩哔哩.exe",
        "aliases": ["B站", "bilibili", "哔哩哔哩", "小破站", "BILIBILI"],
    },
    "QQ": {
        "exe": r"D:\Software\QQ\QQ.exe",
        "aliases": ["qq", "腾讯QQ"],
    },
    "微信": {
        "exe": r"D:\software\Weixin\Weixin.exe",
        "aliases": ["wx", "weixin", "WeChat"],
    },
    "wegame": {
        "exe": r"D:\Games\WeGame\wegame.exe",
        "aliases": ["WeGame", "腾讯游戏平台"],
        "admin": True,
    },
    "原神": {
    "exe": r"D:\Games\miHoYo\miHoYo Launcher\launcher.exe",
    "aliases": ["Genshin", "原", "zzz", "绝区零", "绝"],
    }
}

# ==================== 2. 工具函数 ====================

import ctypes

def launch_app(name: str) -> str:
    """启动白名单内的软件。需要管理员权限的会自动弹 UAC。"""
    if not name or not isinstance(name, str):
        return "错误：软件名不能为空"

    name = name.strip()
    name_lower = name.lower()

    exe = None
    matched_main = None
    need_admin = False

    for main, info in ALLOWED_APPS.items():
        if name == main or name_lower == main.lower():
            exe = info["exe"]
            matched_main = main
            need_admin = info.get("admin", False)
            break
        if any(name_lower == a.lower() for a in info.get("aliases", [])):
            exe = info["exe"]
            matched_main = main
            need_admin = info.get("admin", False)
            break

    if exe is None:
        supported = "、".join(ALLOWED_APPS.keys())
        return f"错误：不支持启动'{name}'。只支持：{supported}"

    # 决定用什么方式启动
    try:
        if need_admin:
            # 用 runas 触发 UAC
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, None, None, 1
            )
            if result <= 32:
                return f"错误：启动失败（ShellExecute 返回 {result}）"
            return f"已启动（需 UAC 确认）：{matched_main}"
        else:
            # 普通启动
            subprocess.Popen(
                exe,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            return f"已启动：{matched_main}（{exe}）"
    except FileNotFoundError:
        return f"错误：找不到程序 {exe}"
    except Exception as e:
        return f"错误：启动失败（{type(e).__name__}: {e}）"


# ==================== 3. 工具说明书 ====================

tools = [
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": (
                "启动电脑上的常用软件。支持白名单软件。"
                "调用后系统会要求用户确认，你不需要自己询问确认。"
                "不区分大小写，用户说别名也可以（如'哔哩哔哩'、'B站'、'微信'、'wx'）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "软件名称，例如 '记事本'、'计算器'"
                    }
                },
                "required": ["name"],
            },
        },
    },
]

TOOL_MAP = {
    "launch_app": launch_app,
}

# ==================== 4. 会话状态 ====================

SYSTEM_PROMPT = """你是一个电脑助手，可以启动电脑上的常用软件。

支持白名单软件。

规则：
- 只处理启动软件相关的问题，其他领域礼貌拒绝
- 当用户要求启动软件时，直接调用 launch_app 工具
- 系统会自动处理"确认"环节，你不需要在对话里问用户"要不要确认"
- 回答简短

示例：
用户：打开记事本
你：（调用 launch_app，参数 name="记事本"）

如果工具返回"错误：..."，如实告诉用户。
"""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
MAX_HISTORY = 20

# ==================== 5. 待确认状态（代码层状态机） ====================

# 结构：{"tool": "launch_app", "args": {...}} 或 None
PENDING = None

# 视为"确认"的词汇
CONFIRM_WORDS = {"确认", "确定", "好", "是", "可以", "同意", "启动吧", "开吧", "yes", "y", "ok"}

# 视为"取消"的词汇
CANCEL_WORDS = {"取消", "不用", "不要", "算了", "否", "不是", "no", "n", "stop"}


def is_confirmation(text: str) -> bool:
    """判断用户是否表达了确认。"""
    t = text.strip().lower()
    # 精确匹配或包含
    return t in CONFIRM_WORDS or any(w in t for w in CONFIRM_WORDS if len(w) > 1)


def is_cancellation(text: str) -> bool:
    """判断用户是否表达了取消。"""
    t = text.strip().lower()
    return t in CANCEL_WORDS or any(w in t for w in CANCEL_WORDS if len(w) > 1)


# ==================== 6. Agent Loop ====================

def call_tool_safe(name: str, args: dict) -> str:
    """实际执行工具（只在确认后调用）。"""
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


def chat(question: str, max_steps: int = 8):
    global conversation, PENDING

    print(f"\n👤 你：{question}")

    # ==================== 先检查 PENDING ====================
    if PENDING is not None:
        call_id = PENDING["call_id"]
        tool = PENDING["tool"]
        args = PENDING["args"]
        display_name = args.get("name", "")

        if is_confirmation(question):
            print(f"   🔧 [已确认] 执行 {tool}({args})")
            result = call_tool_safe(tool, args)
            print(f"      ↳ {result}")

            conversation.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result,
            })
            conversation.append({"role": "user", "content": "确认"})

            try:
                final = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=conversation,
                )
                content = final.choices[0].message.content
                conversation.append(final.choices[0].message.model_dump(exclude_none=True))
                print(f"🤖 它：{content}")
            except Exception as e:
                print(f"🤖 它：（总结失败：{e}）")

            PENDING = None
            trim_history()
            return

        elif is_cancellation(question):
            conversation.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": "用户取消了本次操作，工具未执行。",
            })
            conversation.append({"role": "user", "content": "取消"})
            print(f"🤖 它：好的，已取消。")
            PENDING = None
            trim_history()
            return

        else:
            conversation.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": f"工具未执行，正在等待用户确认启动 {display_name}。",
            })
            print(f"🤖 它：你刚才想启动 {display_name}，请明确回复'确认'或'取消'。")
            # ★ 注意：PENDING 仍然保留，等待下一轮
            return

    # ==================== 正常流程 ====================
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

        # 拦截工具调用
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            print(f"   ⏸️  拦截到工具调用：{name}({args})")
            PENDING = {
                "tool": name,
                "args": args,
                "call_id": tc.id,      # ★ 记住 call_id
            }

            display_name = args.get("name", "")
            print(f"🤖 它：我将启动 {display_name}，请回复'确认'以继续，回复'取消'放弃。")
            return

    print("🤖 它：达到最大步数，无法完成。")
    trim_history()    

def handle(question: str) -> str:
    """
    供外部调用的接口。
    返回回答文本。
    注意：可能有 PENDING 状态。
    """
    global conversation, PENDING

    # ---------- 处理 PENDING ----------
    if PENDING is not None:
        call_id = PENDING["call_id"]
        tool = PENDING["tool"]
        args = PENDING["args"]
        display_name = args.get("name", "")

        if is_confirmation(question):
            result = call_tool_safe(tool, args)
            conversation.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result,
            })
            conversation.append({"role": "user", "content": "确认"})
            try:
                final = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=conversation,
                )
                content = final.choices[0].message.content
                conversation.append(final.choices[0].message.model_dump(exclude_none=True))
                PENDING = None
                trim_history()
                return content or result
            except Exception as e:
                PENDING = None
                return f"（总结失败）{result}"

        elif is_cancellation(question):
            conversation.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": "用户取消了本次操作。",
            })
            conversation.append({"role": "user", "content": "取消"})
            PENDING = None
            trim_history()
            return "好的，已取消。"

        else:
            return f"你刚才想启动 {display_name}，请明确回复'确认'或'取消'。"

    # ---------- 正常流程 ----------
    conversation.append({"role": "user", "content": question})

    for step in range(8):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            tools=tools,
        )
        msg = resp.choices[0].message
        conversation.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            trim_history()
            return msg.content or ""

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            PENDING = {
                "tool": name,
                "args": args,
                "call_id": tc.id,
            }
            display_name = args.get("name", "")
            return f"我将启动 {display_name}，请回复'确认'以继续，回复'取消'放弃。"

    return "（app Agent 达到最大步数）"


def is_pending() -> bool:
    """外部查询：是否有待确认操作"""
    return PENDING is not None

# ==================== 7. 交互入口 ====================

def run_interactive():
    global conversation, PENDING
    print("=" * 60)
    print("软件启动 Agent 已启动。输入 'exit' 退出。")
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
        # 用 handle 处理
        response = handle(user_input)
        print(f"🤖 它：{response}")


if __name__ == "__main__":
    run_interactive()