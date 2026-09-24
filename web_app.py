import json
import re
import datetime
from pathlib import Path

import streamlit as st

import weather_agent
import app_agent

# ==================== 页面配置（必须第一句） ====================

st.set_page_config(
    page_title="我的 AI Agent",
    page_icon="🤖",
    layout="wide",               # 改成宽布局
    initial_sidebar_state="expanded",
)

# ==================== 自定义 CSS ====================

st.markdown("""
<style>
/* 主标题 */
h1 {
    background: linear-gradient(90deg, #4f8bf9, #a259ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

/* 副标题 */
.subtitle {
    color: #888;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

/* 聊天消息圆角 + 阴影 */
.stChatMessage {
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* 侧边栏标题 */
section[data-testid="stSidebar"] h2 {
    font-size: 1.1rem;
    color: #4f8bf9;
}

/* 按钮圆角 */
.stButton > button {
    border-radius: 8px;
    width: 100%;
}

/* 输入框固定宽度 */
.stChatInputContainer {
    padding-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ==================== 头部 ====================

st.markdown("# 🤖 我的 AI Agent")
st.markdown(
    '<div class="subtitle">天气查询 · 数学计算 · 软件启动</div>',
    unsafe_allow_html=True,
)

# ==================== 聊天记录 ====================

HISTORY_FILE = Path(__file__).parent / "chat_history.json"
MAX_SAVED = 200


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_history(messages):
    try:
        trimmed = messages[-MAX_SAVED:]
        HISTORY_FILE.write_text(
            json.dumps(trimmed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        st.warning(f"聊天记录保存失败：{e}")


if "messages" not in st.session_state:
    st.session_state.messages = load_history()

# ==================== 路由 ====================

def route(prompt: str) -> str:
    if app_agent.is_pending():
        return "app"
    p = prompt.lower()
    app_kw = ["打开", "启动", "运行", "开一下", "帮我开", "帮我打开"]
    weather_kw = ["天气", "气温", "温度", "风速", "热不热", "冷不冷",
                  "计算", "等于", "多少", "算一下", "算算", "+", "-", "*", "/", "**"]
    has_app = any(k in p for k in app_kw)
    has_weather = any(k in p for k in weather_kw)
    if has_app and not has_weather:
        return "app"
    if has_weather and not has_app:
        return "weather"
    if has_app and has_weather:
        return "app"
    if len(re.findall(r"\d+", p)) >= 2:
        return "weather"
    return "unknown"


# ==================== 侧边栏 ====================

with st.sidebar:
    st.markdown("## 🎛️ 控制台")
    st.divider()

    # 操作区
    st.markdown("**操作**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空"):
            st.session_state.messages = []
            weather_agent.conversation = [weather_agent.conversation[0]]
            app_agent.conversation = [app_agent.conversation[0]]
            app_agent.PENDING = None
            save_history([])
            st.rerun()
    with col2:
        if st.session_state.messages:
            text = "\n\n".join(
                f"{'👤' if m['role'] == 'user' else '🤖'} {m['content']}"
                for m in st.session_state.messages
            )
            st.download_button(
                "📥 导出",
                text,
                file_name=f"chat_{datetime.datetime.now():%Y%m%d_%H%M}.txt",
                mime="text/plain",
            )

    st.divider()

    # 工具列表
    st.markdown("**可用工具**")
    st.markdown("🌤️ 天气查询")
    st.markdown("🧮 数学计算")
    st.markdown("🚀 启动软件")
    st.caption("（软件需二次确认）")

    st.divider()

    # 会话统计
    st.markdown("**会话统计**")
    n_user = sum(1 for m in st.session_state.messages if m["role"] == "user")
    n_total = len(st.session_state.messages)
    col1, col2 = st.columns(2)
    col1.metric("轮次", n_user)
    col2.metric("消息", n_total)

    st.divider()
    st.caption("Made with ❤️ using Streamlit")

# ==================== 显示历史 ====================

for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ==================== 输入 ====================

prompt = st.chat_input("说点什么…（如：北京天气 / 打开微信 / 2**100）")

if prompt:
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 退出指令
    if prompt.strip().lower() in ("exit", "quit", "退出"):
        answer = "再见！"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        save_history(st.session_state.messages)
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(answer)
        st.stop()

    # 路由 + 调用
    intent = route(prompt)
    try:
        with st.spinner("思考中…"):
            if intent == "weather":
                answer = weather_agent.handle(prompt)
            elif intent == "app":
                answer = app_agent.handle(prompt)
            else:
                answer = "抱歉，我只能帮你查天气、做计算、或启动软件。"
    except Exception as e:
        answer = f"⚠️ 出错了：{type(e).__name__}: {e}"

    # 显示回答
    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_history(st.session_state.messages)
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(answer)