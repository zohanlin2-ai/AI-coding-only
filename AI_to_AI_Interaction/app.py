# Main entry point for the Streamlit application
import time
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load local .env if exists
load_dotenv()

import streamlit as st
from ai_agent import AIAgent, get_random_topic, get_random_name, get_random_role, verify_api_key
from orchestrator import get_next_speaker

def fetch_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
    import urllib.request
    import json
    url = base_url.rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    return models
    except Exception:
        pass
    return ["gemma4:latest"] # fallback

# Set page config
st.set_page_config(
    page_title="AI-to-AI 對話觀測站",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    .title-container {
        background: linear-gradient(135deg, #240b36, #c31432);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(195, 20, 50, 0.25);
    }
    .title-container h1 {
        margin: 0;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
    }
    .title-container p {
        margin: 5px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .sidebar-header {
        font-weight: bold;
        font-size: 1.1rem;
        border-bottom: 2px solid #3d414a;
        padding-bottom: 5px;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    .status-ok {
        background-color: rgba(46, 204, 113, 0.15);
        color: #2ecc71;
        border: 1px solid #2ecc71;
    }
    .status-warning {
        background-color: rgba(241, 196, 15, 0.15);
        color: #f1c40f;
        border: 1px solid #f1c40f;
    }
    .status-missing {
        background-color: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        border: 1px solid #e74c3c;
    }
    .chat-info-card {
        background-color: #1e1e24;
        border-left: 5px solid #c31432;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .agent-card-col {
        background-color: #13151a;
        border: 1px solid #2c2f36;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "session_status" not in st.session_state:
    st.session_state.session_status = "setup"
if "post_dialogue_reason" not in st.session_state:
    st.session_state.post_dialogue_reason = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_running" not in st.session_state:
    st.session_state.is_running = False
st.session_state.is_running = (st.session_state.session_status == "running")
if "current_speaker_index" not in st.session_state:
    st.session_state.current_speaker_index = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "num_ais" not in st.session_state:
    st.session_state.num_ais = 2
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "agents" not in st.session_state:
    st.session_state.agents = []
if "duration_minutes" not in st.session_state:
    st.session_state.duration_minutes = 5
if "pacing_delay" not in st.session_state:
    st.session_state.pacing_delay = 3
if "turn_mode" not in st.session_state:
    st.session_state.turn_mode = "Sequential"
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {}
if "verified_keys" not in st.session_state:
    st.session_state.verified_keys = {"gemini": "", "openai": "", "claude": "", "deepseek": "", "grok": "", "groq": "", "github": "", "ollama": ""}
if "verification_results" not in st.session_state:
    st.session_state.verification_results = {"gemini": "unverified", "openai": "unverified", "claude": "unverified", "deepseek": "unverified", "grok": "unverified", "groq": "unverified", "github": "unverified", "ollama": "unverified"}
if "verification_errors" not in st.session_state:
    st.session_state.verification_errors = {"gemini": "", "openai": "", "claude": "", "deepseek": "", "grok": "", "groq": "", "github": "", "ollama": ""}
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = ["gemma4:latest"]


# Setup initial values for input elements in session state to allow programatic updates
if "input_topic" not in st.session_state:
    st.session_state.input_topic = ""
for i in range(1, 5):
    if f"input_ai{i}_name" not in st.session_state:
        st.session_state[f"input_ai{i}_name"] = ""
    if f"input_ai{i}_role" not in st.session_state:
        st.session_state[f"input_ai{i}_role"] = ""
    if f"input_ai{i}_provider" not in st.session_state:
        st.session_state[f"input_ai{i}_provider"] = "Mock"
    if f"input_ai{i}_model_name" not in st.session_state:
        st.session_state[f"input_ai{i}_model_name"] = "Mock Model"

# Sidebar: API Key Configuration
st.sidebar.markdown('<div class="sidebar-header">🔑 API 金鑰配置</div>', unsafe_allow_html=True)
st.sidebar.info("欲使用真實大模型對話，請在下方填入對應的 API 金鑰。留空則該模型將自動採用 Mock 模擬模式。")

# Load environment variable defaults if available
env_gemini = os.getenv("GEMINI_API_KEY", "")
env_openai = os.getenv("OPENAI_API_KEY", "")
env_claude = os.getenv("CLAUDE_API_KEY", "")
env_deepseek = os.getenv("DEEPSEEK_API_KEY", "")
env_grok = os.getenv("XAI_API_KEY", os.getenv("GROK_API_KEY", ""))
env_groq = os.getenv("GROQ_API_KEY", "")
env_github = os.getenv("GITHUB_TOKEN", os.getenv("GITHUB_PAT", ""))
env_ollama = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_API_BASE", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")))

# Helper to handle key validation state transitions
def update_key_state(provider: str, key_val: str):
    if key_val != st.session_state.verified_keys[provider]:
        st.session_state.verified_keys[provider] = key_val
        st.session_state.verification_results[provider] = "unverified"
        st.session_state.verification_errors[provider] = ""

# 1. Gemini
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=env_gemini)
update_key_state("gemini", gemini_key)
if not gemini_key.strip():
    st.sidebar.markdown("👉 [取得 Gemini API 密鑰](https://aistudio.google.com/)")
else:
    if st.sidebar.button("驗證 Gemini 金鑰", key="btn_verify_gemini"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("Gemini", gemini_key)
            if success:
                st.session_state.verification_results["gemini"] = "verified"
                st.session_state.verification_errors["gemini"] = ""
                st.sidebar.success("🟢 Gemini 金鑰有效！")
            else:
                st.session_state.verification_results["gemini"] = "failed"
                st.session_state.verification_errors["gemini"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 2. OpenAI
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", value=env_openai)
update_key_state("openai", openai_key)
if not openai_key.strip():
    st.sidebar.markdown("👉 [取得 OpenAI API 密鑰](https://platform.openai.com/api-keys)")
else:
    if st.sidebar.button("驗證 OpenAI 金鑰", key="btn_verify_openai"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("OpenAI", openai_key)
            if success:
                st.session_state.verification_results["openai"] = "verified"
                st.session_state.verification_errors["openai"] = ""
                st.sidebar.success("🟢 OpenAI 金鑰有效！")
            else:
                st.session_state.verification_results["openai"] = "failed"
                st.session_state.verification_errors["openai"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 3. Claude
claude_key = st.sidebar.text_input("Claude (Anthropic) API Key", type="password", value=env_claude)
update_key_state("claude", claude_key)
if not claude_key.strip():
    st.sidebar.markdown("👉 [取得 Claude API 密鑰](https://console.anthropic.com/)")
else:
    if st.sidebar.button("驗證 Claude 金鑰", key="btn_verify_claude"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("Claude", claude_key)
            if success:
                st.session_state.verification_results["claude"] = "verified"
                st.session_state.verification_errors["claude"] = ""
                st.sidebar.success("🟢 Claude 金鑰有效！")
            else:
                st.session_state.verification_results["claude"] = "failed"
                st.session_state.verification_errors["claude"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 4. DeepSeek
deepseek_key = st.sidebar.text_input("DeepSeek API Key", type="password", value=env_deepseek)
update_key_state("deepseek", deepseek_key)
if not deepseek_key.strip():
    st.sidebar.markdown("👉 [取得 DeepSeek API 密鑰](https://platform.deepseek.com/api_keys)")
else:
    if st.sidebar.button("驗證 DeepSeek 金鑰", key="btn_verify_deepseek"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("DeepSeek", deepseek_key)
            if success:
                st.session_state.verification_results["deepseek"] = "verified"
                st.session_state.verification_errors["deepseek"] = ""
                st.sidebar.success("🟢 DeepSeek 金鑰有效！")
            else:
                st.session_state.verification_results["deepseek"] = "failed"
                st.session_state.verification_errors["deepseek"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 5. Grok
grok_key = st.sidebar.text_input("Grok API Key", type="password", value=env_grok)
update_key_state("grok", grok_key)
if not grok_key.strip():
    st.sidebar.markdown("👉 [取得 Grok API 密鑰](https://console.x.ai/)")
else:
    if st.sidebar.button("驗證 Grok 金鑰", key="btn_verify_grok"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("Grok", grok_key)
            if success:
                st.session_state.verification_results["grok"] = "verified"
                st.session_state.verification_errors["grok"] = ""
                st.sidebar.success("🟢 Grok 金鑰有效！")
            else:
                st.session_state.verification_results["grok"] = "failed"
                st.session_state.verification_errors["grok"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 6. Groq
groq_key = st.sidebar.text_input("Groq API Key", type="password", value=env_groq)
update_key_state("groq", groq_key)
if not groq_key.strip():
    st.sidebar.markdown("👉 [取得 Groq API 密鑰](https://console.groq.com/)")
else:
    if st.sidebar.button("驗證 Groq 金鑰", key="btn_verify_groq"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("Groq", groq_key)
            if success:
                st.session_state.verification_results["groq"] = "verified"
                st.session_state.verification_errors["groq"] = ""
                st.sidebar.success("🟢 Groq 金鑰有效！")
            else:
                st.session_state.verification_results["groq"] = "failed"
                st.session_state.verification_errors["groq"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 7. GitHub Models
github_key = st.sidebar.text_input("GitHub Token (PAT)", type="password", value=env_github)
update_key_state("github", github_key)
if not github_key.strip():
    st.sidebar.markdown("👉 [取得 GitHub 權杖 (PAT)](https://github.com/settings/tokens)")
else:
    if st.sidebar.button("驗證 GitHub 金鑰", key="btn_verify_github"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("GitHub", github_key)
            if success:
                st.session_state.verification_results["github"] = "verified"
                st.session_state.verification_errors["github"] = ""
                st.sidebar.success("🟢 GitHub 金鑰有效！")
            else:
                st.session_state.verification_results["github"] = "failed"
                st.session_state.verification_errors["github"] = msg
                st.sidebar.error(f"🔴 {msg}")

# 8. Ollama Local Endpoint
ollama_url = st.sidebar.text_input("Ollama API 位址", value=env_ollama)
update_key_state("ollama", ollama_url)
if not ollama_url.strip():
    st.sidebar.markdown("👉 本地預設位址: `http://localhost:11434`")
else:
    # Automatic check at startup if unverified
    if st.session_state.verification_results["ollama"] == "unverified":
        success, msg = verify_api_key("Ollama", ollama_url)
        if success:
            st.session_state.verification_results["ollama"] = "verified"
            st.session_state.verification_errors["ollama"] = ""
            st.session_state.ollama_models = fetch_ollama_models(ollama_url)
        else:
            st.session_state.verification_results["ollama"] = "failed"
            st.session_state.verification_errors["ollama"] = msg

    if st.sidebar.button("驗證 Ollama 連線", key="btn_verify_ollama"):
        with st.sidebar.spinner("驗證中..."):
            success, msg = verify_api_key("Ollama", ollama_url)
            if success:
                st.session_state.verification_results["ollama"] = "verified"
                st.session_state.verification_errors["ollama"] = ""
                st.sidebar.success("🟢 Ollama 連線成功！")
                st.session_state.ollama_models = fetch_ollama_models(ollama_url)
            else:
                st.session_state.verification_results["ollama"] = "failed"
                st.session_state.verification_errors["ollama"] = msg
                st.sidebar.error(f"🔴 {msg}")

# API Status indicators
st.sidebar.markdown('<div class="sidebar-header">📡 API 連線狀態</div>', unsafe_allow_html=True)

def show_status(name: str, provider_key: str, key_val: str):
    status = st.session_state.verification_results.get(provider_key, "unverified")
    if provider_key == "ollama":
        if not key_val.strip():
            st.sidebar.markdown(f"**{name}**: <span class='status-badge status-missing'>🔴 未配置</span>", unsafe_allow_html=True)
        elif status == "verified":
            st.sidebar.markdown(f"**{name}**: <span class='status-badge status-ok'>🟢 連線成功</span>", unsafe_allow_html=True)
        elif status == "failed":
            err_msg = st.session_state.verification_errors.get(provider_key, "")
            st.sidebar.markdown(f"**{name}**: <span class='status-badge status-missing'>❌ 連線失敗</span>", unsafe_allow_html=True)
            st.sidebar.caption(f"⚠️ {err_msg}")
        else:
            st.sidebar.markdown(f"**{name}**: <span class='status-badge status-warning'>🟡 已配置 (未驗證)</span>", unsafe_allow_html=True)
        return

    if not key_val.strip():
        st.sidebar.markdown(f"**{name}**: <span class='status-badge status-missing'>🔴 未配置</span>", unsafe_allow_html=True)
    elif status == "verified":
        st.sidebar.markdown(f"**{name}**: <span class='status-badge status-ok'>🟢 驗證成功</span>", unsafe_allow_html=True)
    elif status == "failed":
        err_msg = st.session_state.verification_errors.get(provider_key, "")
        st.sidebar.markdown(f"**{name}**: <span class='status-badge status-missing'>❌ 驗證失敗</span>", unsafe_allow_html=True)
        st.sidebar.caption(f"⚠️ {err_msg}")
    else:
        st.sidebar.markdown(f"**{name}**: <span class='status-badge status-warning'>🟡 已配置 (未驗證)</span>", unsafe_allow_html=True)

show_status("Gemini", "gemini", gemini_key)
show_status("OpenAI", "openai", openai_key)
show_status("Claude", "claude", claude_key)
show_status("DeepSeek", "deepseek", deepseek_key)
show_status("Grok", "grok", grok_key)
show_status("Groq", "groq", groq_key)
show_status("GitHub Models", "github", github_key)
show_status("Ollama (本地)", "ollama", ollama_url)

# Update session API keys
st.session_state.api_keys = {
    "gemini": gemini_key,
    "openai": openai_key,
    "claude": claude_key,
    "deepseek": deepseek_key,
    "grok": grok_key,
    "groq": groq_key,
    "github": github_key,
    "ollama": ollama_url
}

# Sidebar: Simulation settings
st.sidebar.markdown('<div class="sidebar-header">⚙️ 對話運行設定</div>', unsafe_allow_html=True)

duration_minutes = st.sidebar.slider(
    "對話總時長 (分鐘)", 
    min_value=1, 
    max_value=120, 
    value=st.session_state.duration_minutes,
    help="對話將在計時結束時自動終止。最少 1 分鐘，最多 120 分鐘。"
)
st.session_state.duration_minutes = duration_minutes

pacing_delay = st.sidebar.slider(
    "發言時間間隔 (秒)", 
    min_value=1, 
    max_value=15, 
    value=st.session_state.pacing_delay,
    help="每次 AI 發言完畢後，等待下一個 AI 發言的秒數，以便人類閱讀。"
)
st.session_state.pacing_delay = pacing_delay

turn_mode_cn = st.sidebar.selectbox(
    "發言順序邏輯",
    options=["輪流模式 (Sequential)", "點名接力模式 (Nomination)", "中央協調模式 (Orchestrator)"],
    index=0,
    help="輪流：AI依序發言。點名接力：AI可在說話最後使用 @角色名 點名接力。中央協調：每次由協調大模型根據話題決定誰最適合接話。"
)
if "輪流" in turn_mode_cn:
    st.session_state.turn_mode = "Sequential"
elif "點名" in turn_mode_cn:
    st.session_state.turn_mode = "Nomination"
else:
    st.session_state.turn_mode = "Orchestrator"


# Main Title Header
st.markdown("""
<div class="title-container">
    <h1>🌌 AI-to-AI 對話觀測站</h1>
    <p>設定主題與不同的人設，即時觀測多個 AI 在對話室中的思維交鋒與對談！</p>
</div>
""", unsafe_allow_html=True)


# Randomizer Logic Functions
def randomize_blanks():
    """Fills in empty topic, names, or roles with random values."""
    if not st.session_state.input_topic.strip():
        st.session_state.input_topic = get_random_topic()
        
    chosen_names = []
    chosen_roles = []
    
    # Gather existing inputs
    for i in range(1, 5):
        n = st.session_state.get(f"input_ai{i}_name", "").strip()
        r = st.session_state.get(f"input_ai{i}_role", "").strip()
        if n: chosen_names.append(n)
        if r: chosen_roles.append(r)
        
    # Fill empty ones
    for i in range(1, 5):
        n_key = f"input_ai{i}_name"
        r_key = f"input_ai{i}_role"
        
        if not st.session_state.get(n_key, "").strip():
            rand_name = get_random_name(exclude=chosen_names)
            st.session_state[n_key] = rand_name
            chosen_names.append(rand_name)
            
        if not st.session_state.get(r_key, "").strip():
            rand_role = get_random_role(exclude=chosen_roles)
            st.session_state[r_key] = rand_role
            chosen_roles.append(rand_role)

def randomize_all():
    """Forces all topic, names, and roles to be randomly generated."""
    st.session_state.input_topic = get_random_topic()
    chosen_names = []
    chosen_roles = []
    for i in range(1, 5):
        n_key = f"input_ai{i}_name"
        r_key = f"input_ai{i}_role"
        
        rand_name = get_random_name(exclude=chosen_names)
        st.session_state[n_key] = rand_name
        chosen_names.append(rand_name)
        
        rand_role = get_random_role(exclude=chosen_roles)
        st.session_state[r_key] = rand_role
        chosen_roles.append(rand_role)


# Helper to list non-failed providers
def get_available_providers():
    providers = ["Mock"]
    for p in ["Gemini", "OpenAI", "Claude", "DeepSeek", "Grok", "Groq", "GitHub", "Ollama"]:
        key_val = st.session_state.api_keys.get(p.lower(), "")
        status = st.session_state.verification_results.get(p.lower(), "unverified")
        if key_val.strip() and status != "failed":
            providers.append(p)
    return providers

def sync_inputs_from_agents():
    """Sync input form fields from the currently running agents.
    
    Call this before entering any editing state so the form always reflects
    the actual parameters used in the last dialogue, not stale form state.
    """
    agents = st.session_state.get("agents", [])
    st.session_state.input_topic = st.session_state.get("topic", "")
    st.session_state.num_ais = len(agents) if agents else st.session_state.get("num_ais", 2)
    for i, agent in enumerate(agents):
        n = i + 1
        st.session_state[f"input_ai{n}_name"] = agent.name
        st.session_state[f"input_ai{n}_role"] = agent.role
        st.session_state[f"input_ai{n}_provider"] = agent.model_provider
        st.session_state[f"input_ai{n}_model_name"] = agent.model_name

# ------------------- VIEW: CONFIGURATION PANEL -------------------
if st.session_state.session_status in ["setup", "editing_continue", "editing_restart"]:
    
    st.subheader("📝 第一步：設定主題與 AI 人數")
    
    topic = st.text_input(
        "💬 討論主題", 
        value=st.session_state.input_topic, 
        placeholder="例如：人工智慧是否應該擁有投票權？", 
        key="input_topic"
    )
    
    num_ais = st.slider(
        "👥 參與 AI 數量", 
        min_value=1, 
        max_value=4, 
        value=st.session_state.num_ais, 
        step=1,
        key="num_ais"
    )
    
    st.subheader("🎭 第二步：配置 AI 的角色與模型")
    
    cols = st.columns(num_ais)
    
    # Store temporary configurations
    configured_agents = []
    
    for idx, col in enumerate(cols):
        agent_num = idx + 1
        with col:
            st.markdown(f'<div class="agent-card-col"><strong>🤖 AI #{agent_num}</strong>', unsafe_allow_html=True)
            
            # Input fields mapped to session_state keys for automatic updates
            name = st.text_input(
                f"角色名稱 #{agent_num}", 
                key=f"input_ai{agent_num}_name",
                placeholder="例如：老張"
            )
            
            role = st.text_input(
                f"角色設定/定位 #{agent_num}", 
                key=f"input_ai{agent_num}_role",
                placeholder="例如：冷靜理性的經濟學家"
            )
            
            available_providers = get_available_providers()
            current_provider = st.session_state.get(f"input_ai{agent_num}_provider", "Mock")
            if current_provider not in available_providers:
                st.session_state[f"input_ai{agent_num}_provider"] = "Mock"
                st.session_state[f"input_ai{agent_num}_model_name"] = "Mock Model"
                
            provider = st.selectbox(
                f"模型提供商 #{agent_num}",
                options=available_providers,
                key=f"input_ai{agent_num}_provider"
            )
            
            # Model name options based on provider
            model_options = {
                "Mock": ["Mock Model"],
                "Gemini": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
                "OpenAI": ["gpt-4o-mini", "gpt-4o", "o1-mini"],
                "Claude": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-5-haiku-20241022"],
                "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
                "Grok": ["grok-2-1212", "grok-beta"],
                "Groq": ["gemma2-9b-it", "llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
                "GitHub": ["gpt-4o-mini", "gpt-4o", "meta-llama-3.1-8b-instruct", "cohere-command-r-plus"],
                "Ollama": st.session_state.ollama_models
            }
            
            # Safety check: in case model name is out of sync with selected provider
            curr_model = st.session_state.get(f"input_ai{agent_num}_model_name", "Mock Model")
            if curr_model not in model_options.get(provider, ["Mock Model"]):
                st.session_state[f"input_ai{agent_num}_model_name"] = model_options.get(provider, ["Mock Model"])[0]

            model_name = st.selectbox(
                f"具體模型 #{agent_num}",
                options=model_options[provider],
                key=f"input_ai{agent_num}_model_name"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Record config
            configured_agents.append({
                "agent_id": idx,
                "name": name,
                "role": role,
                "model_provider": provider,
                "model_name": model_name
            })
            
    # Action buttons
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
    
    with btn_col1:
        st.button("🎲 隨機補全空白欄位", on_click=randomize_blanks, use_container_width=True)
    with btn_col2:
        st.button("🔄 隨機重設所有配置", on_click=randomize_all, use_container_width=True)
        
    with btn_col3:
        button_label = "🚀 繼續對話" if st.session_state.session_status == "editing_continue" else "🚀 開始對話"
        start_btn = st.button(button_label, type="primary", use_container_width=True)
        
    if start_btn:
        # Check and handle blanks before starting
        final_topic = st.session_state.input_topic.strip()
        if not final_topic:
            final_topic = get_random_topic()
            st.session_state.input_topic = final_topic
            
        final_agents = []
        chosen_names = []
        chosen_roles = []
        
        # Resolve names and roles for the active number of agents
        for idx in range(num_ais):
            agent_num = idx + 1
            n_key = f"input_ai{agent_num}_name"
            r_key = f"input_ai{agent_num}_role"
            p_key = f"input_ai{agent_num}_provider"
            m_key = f"input_ai{agent_num}_model_name"
            
            n_val = st.session_state[n_key].strip()
            r_val = st.session_state[r_key].strip()
            p_val = st.session_state[p_key]
            m_val = st.session_state[m_key]
            
            if not n_val:
                n_val = get_random_name(exclude=chosen_names)
                st.session_state[n_key] = n_val
            chosen_names.append(n_val)
                
            if not r_val:
                r_val = get_random_role(exclude=chosen_roles)
                st.session_state[r_key] = r_val
            chosen_roles.append(r_val)
                
            # Instantiate AIAgent
            final_agents.append(AIAgent(
                agent_id=idx,
                name=n_val,
                role=r_val,
                model_provider=p_val,
                model_name=m_val
            ))
            
        # Initialize running states
        st.session_state.topic = final_topic
        st.session_state.agents = final_agents
        
        if st.session_state.session_status == "editing_continue":
            if final_agents:
                st.session_state.current_speaker_index = st.session_state.current_speaker_index % len(final_agents)
        else:
            st.session_state.chat_history = []
            st.session_state.current_speaker_index = 0
            
        st.session_state.start_time = time.time()
        st.session_state.session_status = "running"
        st.session_state.is_running = True
        st.rerun()

    # ------------------- VIEW: EXPORT AND SAVE DIALOGUE (PREVIOUS SESSION) -------------------
    if len(st.session_state.chat_history) > 0:
        st.markdown("---")
        st.subheader("💾 上一次對話結果與匯出")
        
        # Format the markdown transcript
        lines = []
        lines.append(f"# 聊天主題：{st.session_state.topic}\n")
        lines.append("## 參與 AI 角色名單：")
        for agent in st.session_state.agents:
            lines.append(f"- **{agent.name}** (角色設定: {agent.role}) [模型: {agent.model_provider} - {agent.model_name}]")
        lines.append("\n---\n")
        
        for msg in st.session_state.chat_history:
            provider_str = f" | 來自 {msg.get('model_provider', 'Mock')}"
            lines.append(f"[{msg['name']} ({msg['role']}{provider_str})]: {msg['text']}\n")
            
        transcript_content = "\n".join(lines)
        
        st.info("您可以點選下方按鈕儲存對話存檔。內容會完整記錄主題、各 AI 的角色設定、以及對話紀錄。")
        
        # Download button
        st.download_button(
            label="📥 儲存並下載對話內容 (.md)",
            data=transcript_content,
            file_name=f"AI_Chat_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # Review display
        with st.expander("👀 預覽上一次對話內容"):
            st.markdown(f"**主題：{st.session_state.topic}**")
            for msg in st.session_state.chat_history:
                provider_str = f" | 來自 {msg.get('model_provider', 'Mock')}"
                st.write(f"**{msg['name']} ({msg['role']}{provider_str})**： {msg['text']}")
                
        # Clear button
        if st.button("🗑️ 清除歷史紀錄", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

# ------------------- VIEW: LIVE DIALOGUE SIMULATION -------------------
elif st.session_state.session_status == "running":
    # Display running details
    st.markdown(f"""
    <div class="chat-info-card">
         <h3>💬 討論主題：{st.session_state.topic}</h3>
        <p>發言順序模式：{turn_mode_cn} | 發言間隔：{st.session_state.pacing_delay}秒</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Calculate time
    elapsed = time.time() - st.session_state.start_time
    total_seconds = st.session_state.duration_minutes * 60
    remaining = max(0.0, total_seconds - elapsed)
    
    rem_min = int(remaining // 60)
    rem_sec = int(remaining % 60)
    
    # Progress bar and Stop button
    col_timer, col_stop = st.columns([5, 1])
    with col_timer:
        progress_val = min(1.0, elapsed / total_seconds)
        st.progress(progress_val)
        st.write(f"⏱️ 剩餘時間：{rem_min} 分 {rem_sec} 秒 / 總時間設定：{st.session_state.duration_minutes} 分鐘")
        
    with col_stop:
        if st.button("🛑 停止對話", type="primary", use_container_width=True):
            st.session_state.session_status = "post_dialogue"
            st.session_state.post_dialogue_reason = "manual_stop"
            st.rerun()
            
    # Check if time has expired
    if remaining <= 0:
        st.session_state.session_status = "post_dialogue"
        st.session_state.post_dialogue_reason = "time_expired"
        st.rerun()
        
    # Render entire dialogue history
    st.markdown("### 💬 對話聊天室")
    
    # Emojis for avatars
    avatars = ["🧑‍🎤", "🧙‍♂️", "🕵️‍♂️", "👩‍🚀"]
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg.get("avatar", "🤖")):
            provider_str = f" - 來自 {msg.get('model_provider', 'Mock')}"
            st.markdown(f"**{msg['name']}** <span style='color: gray; font-size: 0.85rem;'>({msg['role']}{provider_str})</span>", unsafe_allow_html=True)
            st.write(msg["text"])
            
    # Generate next message if we are running
    current_agent = st.session_state.agents[st.session_state.current_speaker_index]
    
    # Visual typing indicator
    with st.chat_message(avatars[st.session_state.current_speaker_index % len(avatars)]):
        st.markdown(f"**{current_agent.name}** <span style='color: gray; font-size: 0.85rem;'>({current_agent.role} - 來自 {current_agent.model_provider})</span> 正在思考中...", unsafe_allow_html=True)
        with st.spinner(""):
            # Fetch reply from AI agent
            reply = current_agent.get_response(
                topic=st.session_state.topic,
                conversation_history=st.session_state.chat_history,
                all_agents=st.session_state.agents,
                api_keys=st.session_state.api_keys
            )
            
    # Add new message to state
    new_msg = {
        "name": current_agent.name,
        "role": current_agent.role,
        "text": reply,
        "model_provider": current_agent.model_provider,
        "avatar": avatars[st.session_state.current_speaker_index % len(avatars)]
    }
    st.session_state.chat_history.append(new_msg)
    
    # Calculate next speaker
    next_idx = get_next_speaker(
        mode=st.session_state.turn_mode,
        current_index=st.session_state.current_speaker_index,
        agents=st.session_state.agents,
        last_message_text=reply,
        topic=st.session_state.topic,
        conversation_history=st.session_state.chat_history,
        api_keys=st.session_state.api_keys
    )
    st.session_state.current_speaker_index = next_idx
    
    # Sleep for spacing delay
    time.sleep(st.session_state.pacing_delay)
    
    # Rerun stream to update UI
    st.rerun()

# ------------------- VIEW: POST DIALOGUE ACTIONS -------------------
elif st.session_state.session_status == "post_dialogue":
    st.subheader("🏁 對話已結束")
    
    # Show status notification
    if st.session_state.post_dialogue_reason == "time_expired":
        st.success("⏱️ 設定時間到！對話已自動結束。")
    elif st.session_state.post_dialogue_reason == "manual_stop":
        st.warning("🛑 對話已由使用者手動結束。")
        
    st.markdown("### 🎯 請選擇後續動作")
    
    # 5 Action Options
    opt_col1, opt_col2 = st.columns(2)
    
    with opt_col1:
        if st.button("💬 1. 不修改參數，繼續對話", help="保留目前對話紀錄，以相同的參數設定繼續對話", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.session_status = "running"
            st.rerun()
            
        if st.button("⚙️ 2. 修改參數，繼續對話", help="保留目前對話紀錄，進入設定畫面調整參數後繼續對話", use_container_width=True):
            sync_inputs_from_agents()
            st.session_state.session_status = "editing_continue"
            st.rerun()
            
        if st.button("🔄 3. 不修改參數，重新對話", help="清除對話紀錄，以相同的參數設定重新開始對話", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.current_speaker_index = 0
            st.session_state.start_time = time.time()
            st.session_state.session_status = "running"
            st.rerun()
            
    with opt_col2:
        if st.button("📝 4. 修改參數，重新對話", help="清除對話紀錄，進入設定畫面重新調整參數後開始新對話", use_container_width=True):
            sync_inputs_from_agents()
            st.session_state.chat_history = []
            st.session_state.current_speaker_index = 0
            st.session_state.session_status = "editing_restart"
            st.rerun()
            
        if st.button("🚪 5. 結束對話", type="primary", help="清除對話紀錄與設定，返回初始畫面", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.current_speaker_index = 0
            st.session_state.session_status = "setup"
            st.rerun()
            
    st.markdown("---")
    st.subheader("💾 對話結果與匯出")
    
    if len(st.session_state.chat_history) > 0:
        # Format the markdown transcript
        lines = []
        lines.append(f"# 聊天主題：{st.session_state.topic}\n")
        lines.append("## 參與 AI 角色名單：")
        for agent in st.session_state.agents:
            lines.append(f"- **{agent.name}** (角色設定: {agent.role}) [模型: {agent.model_provider} - {agent.model_name}]")
        lines.append("\n---\n")
        
        for msg in st.session_state.chat_history:
            provider_str = f" | 來自 {msg.get('model_provider', 'Mock')}"
            lines.append(f"[{msg['name']} ({msg['role']}{provider_str})]: {msg['text']}\n")
            
        transcript_content = "\n".join(lines)
        
        st.info("您可以點選下方按鈕儲存對話存檔。內容會完整記錄主題、各 AI 的角色設定、以及對話紀錄。")
        
        # Download button
        st.download_button(
            label="📥 儲存並下載對話內容 (.md)",
            data=transcript_content,
            file_name=f"AI_Chat_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # Review display
        with st.expander("👀 預覽本次對話內容", expanded=True):
            st.markdown(f"**主題：{st.session_state.topic}**")
            for msg in st.session_state.chat_history:
                provider_str = f" | 來自 {msg.get('model_provider', 'Mock')}"
                st.write(f"**{msg['name']} ({msg['role']}{provider_str})**： {msg['text']}")
