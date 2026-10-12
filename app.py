"""
Productive Agent — Streamlit UI  (Premium Redesign)
=====================================================
Run:  python -m streamlit run app.py
"""

import os
import sys
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
AGENT_DIR = ROOT / "agent"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(AGENT_DIR))

os.environ.setdefault("TASK_DB_PATH",    str(ROOT / "data" / "tasks.db"))
os.environ.setdefault("USER_PREFS_PATH", str(ROOT / "data" / "user_preferences.json"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import streamlit as st

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Productive Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── design system ─────────────────────────────────────────────────────────────
THEME = {
    "bg":          "#080c14",
    "surface":     "#0d1117",
    "surface2":    "#161b27",
    "border":      "#1e2d45",
    "accent":      "#4f8ef7",
    "accent2":     "#a78bfa",
    "accent3":     "#34d399",
    "text":        "#e6edf3",
    "text_muted":  "#7d8fa9",
    "danger":      "#f87171",
    "warning":     "#fbbf24",
    "success":     "#34d399",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── reset & base ── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; }}
html, body, [class*="css"], .stApp {{
    background-color: {THEME['bg']} !important;
    color: {THEME['text']};
    font-family: 'Inter', -apple-system, sans-serif;
}}

/* ── hide streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1.5rem 2rem 2rem !important; max-width: 100% !important; }}

/* ── sidebar ── */
[data-testid="stSidebar"] {{
    background: {THEME['surface']} !important;
    border-right: 1px solid {THEME['border']} !important;
    width: 260px !important;
}}
[data-testid="stSidebar"] > div {{ padding: 1.5rem 1rem; }}
[data-testid="stSidebar"] * {{ color: {THEME['text']} !important; }}

/* sidebar logo */
.sidebar-logo {{
    display: flex; align-items: center; gap: 10px;
    padding: 0 4px 20px;
    border-bottom: 1px solid {THEME['border']};
    margin-bottom: 20px;
}}
.sidebar-logo-icon {{
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, {THEME['accent']}, {THEME['accent2']});
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700; color: white;
    box-shadow: 0 0 20px rgba(79,142,247,0.4);
}}
.sidebar-logo-text {{ font-size: 15px; font-weight: 700; color: {THEME['text']} !important; }}
.sidebar-logo-sub  {{ font-size: 11px; color: {THEME['text_muted']} !important; }}

/* nav section label */
.nav-section-label {{
    font-size: 10px; font-weight: 600; letter-spacing: 1.2px;
    color: {THEME['text_muted']} !important;
    text-transform: uppercase;
    padding: 0 4px; margin: 16px 0 6px;
}}

/* nav buttons */
[data-testid="stSidebar"] .stButton > button {{
    width: 100%; background: transparent !important;
    border: none !important; border-radius: 8px !important;
    color: {THEME['text_muted']} !important;
    text-align: left !important; padding: 8px 12px !important;
    font-size: 13px !important; font-weight: 500 !important;
    transition: all 0.15s ease !important; margin: 1px 0 !important;
    display: flex; align-items: center;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: {THEME['surface2']} !important;
    color: {THEME['text']} !important;
}}
.nav-active > button {{
    background: linear-gradient(90deg, rgba(79,142,247,0.15), transparent) !important;
    color: {THEME['accent']} !important;
    border-left: 2px solid {THEME['accent']} !important;
    padding-left: 10px !important;
}}

/* ── page header ── */
.page-header {{
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 20px; margin-bottom: 24px;
    border-bottom: 1px solid {THEME['border']};
}}
.page-header-icon {{
    width: 40px; height: 40px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}}
.page-header-title {{ font-size: 22px; font-weight: 700; color: {THEME['text']}; }}
.page-header-sub   {{ font-size: 13px; color: {THEME['text_muted']}; margin-top: 2px; }}

/* ── glass card ── */
.glass-card {{
    background: {THEME['surface']}; border: 1px solid {THEME['border']};
    border-radius: 14px; padding: 18px 20px; margin-bottom: 12px;
    transition: border-color 0.2s;
}}
.glass-card:hover {{ border-color: {THEME['accent']}40; }}

/* ── chat ── */
.chat-wrap {{
    display: flex; flex-direction: column; gap: 6px;
    padding: 4px 0;
}}
.msg-row-user  {{ display: flex; justify-content: flex-end; }}
.msg-row-agent {{ display: flex; justify-content: flex-start; }}

.bubble-user {{
    background: linear-gradient(135deg, {THEME['accent']}, {THEME['accent2']});
    color: white; padding: 11px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 72%; font-size: 14px; line-height: 1.5;
    box-shadow: 0 4px 20px rgba(79,142,247,0.25);
    word-break: break-word;
}}
.bubble-agent {{
    background: {THEME['surface2']}; color: {THEME['text']};
    padding: 11px 16px;
    border-radius: 18px 18px 18px 4px;
    max-width: 78%; font-size: 14px; line-height: 1.6;
    border: 1px solid {THEME['border']};
    word-break: break-word;
}}
.bubble-agent code {{
    font-family: 'JetBrains Mono', monospace;
    background: {THEME['bg']}; padding: 2px 6px;
    border-radius: 4px; font-size: 12px;
    color: {THEME['accent3']};
}}
.msg-ts {{
    font-size: 10px; color: {THEME['text_muted']};
    padding: 0 4px; margin-top: 2px; text-align: right;
}}

/* input row */
.stForm {{ margin-top: 12px; }}
[data-testid="stTextInput"] input {{
    background: {THEME['surface2']} !important;
    border: 1px solid {THEME['border']} !important;
    border-radius: 12px !important;
    color: {THEME['text']} !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {THEME['accent']} !important;
    box-shadow: 0 0 0 2px rgba(79,142,247,0.15) !important;
}}
[data-testid="stTextInput"] input::placeholder {{
    color: {THEME['text_muted']} !important;
}}

/* ── send button ── */
.stForm [data-testid="baseButton-secondary"],
.stForm [data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, {THEME['accent']}, {THEME['accent2']}) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; font-weight: 600 !important;
    font-size: 14px !important;
    box-shadow: 0 4px 15px rgba(79,142,247,0.3) !important;
    transition: opacity 0.15s !important;
}}
.stForm [data-testid="baseButton-secondary"]:hover,
.stForm [data-testid="baseButton-primary"]:hover {{
    opacity: 0.9 !important;
}}

/* ── task card ── */
.task-card {{
    background: {THEME['surface']}; border: 1px solid {THEME['border']};
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
    transition: transform 0.15s, border-color 0.15s;
    position: relative; overflow: hidden;
}}
.task-card::before {{
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 3px; border-radius: 3px 0 0 3px;
}}
.task-card.high::before   {{ background: {THEME['danger']}; }}
.task-card.medium::before {{ background: {THEME['warning']}; }}
.task-card.low::before    {{ background: {THEME['success']}; }}
.task-card:hover {{
    transform: translateY(-1px);
    border-color: {THEME['accent']}50;
}}
.task-title {{
    font-size: 14px; font-weight: 600; color: {THEME['text']};
    margin-bottom: 6px;
}}
.task-badges {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }}
.badge {{
    font-size: 11px; font-weight: 500; padding: 2px 8px;
    border-radius: 20px; display: inline-block;
}}
.badge-todo       {{ background: rgba(79,142,247,0.15); color: {THEME['accent']}; }}
.badge-in_progress{{ background: rgba(251,191,36,0.15);  color: {THEME['warning']}; }}
.badge-done       {{ background: rgba(52,211,153,0.15);  color: {THEME['success']}; }}
.badge-high       {{ background: rgba(248,113,113,0.15); color: {THEME['danger']}; }}
.badge-medium     {{ background: rgba(251,191,36,0.15);  color: {THEME['warning']}; }}
.badge-low        {{ background: rgba(52,211,153,0.15);  color: {THEME['success']}; }}
.task-desc {{
    font-size: 12px; color: {THEME['text_muted']};
    margin-top: 6px; line-height: 1.5;
}}
.task-due {{
    font-size: 11px; color: {THEME['text_muted']};
    font-family: 'JetBrains Mono', monospace;
}}

/* ── day group header ── */
.day-label {{
    font-size: 12px; font-weight: 600; color: {THEME['text_muted']};
    letter-spacing: 0.5px; text-transform: uppercase;
    padding: 6px 0; margin: 16px 0 8px;
    border-bottom: 1px solid {THEME['border']};
    display: flex; align-items: center; gap: 8px;
}}
.day-today   {{ color: {THEME['accent']}; }}
.day-count {{
    background: {THEME['surface2']}; padding: 1px 7px;
    border-radius: 10px; font-size: 11px;
}}

/* ── stat cards (tasks page) ── */
.stat-card {{
    background: {THEME['surface']}; border: 1px solid {THEME['border']};
    border-radius: 14px; padding: 18px 22px; text-align: center;
}}
.stat-number {{
    font-size: 32px; font-weight: 700;
    background: linear-gradient(135deg, {THEME['accent']}, {THEME['accent2']});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.stat-label {{
    font-size: 12px; color: {THEME['text_muted']}; margin-top: 4px;
}}

/* ── search result ── */
.search-card {{
    background: {THEME['surface']}; border: 1px solid {THEME['border']};
    border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
    transition: border-color 0.2s;
}}
.search-card:hover {{ border-color: {THEME['accent']}50; }}
.search-card-title {{
    font-size: 14px; font-weight: 600;
    color: {THEME['accent']}; margin-bottom: 6px;
}}
.search-card-snippet {{
    font-size: 13px; color: {THEME['text_muted']}; line-height: 1.5;
    margin-bottom: 8px;
}}
.search-card-url {{
    font-size: 11px; color: {THEME['text_muted']};
    font-family: 'JetBrains Mono', monospace;
    opacity: 0.7;
}}

/* ── approval card ── */
.approval-card {{
    background: linear-gradient(135deg, rgba(251,191,36,0.08), rgba(251,191,36,0.03));
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 14px; padding: 20px 22px; margin: 16px 0;
}}
.approval-title {{
    font-size: 15px; font-weight: 700; color: {THEME['warning']};
    margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}}
.approval-preview {{
    background: {THEME['bg']}; border: 1px solid {THEME['border']};
    border-radius: 10px; padding: 14px 16px;
    font-size: 13px; font-family: 'JetBrains Mono', monospace;
    color: {THEME['text']}; line-height: 1.6; margin-bottom: 14px;
    white-space: pre-wrap;
}}

/* ── expander ── */
[data-testid="stExpander"] {{
    background: {THEME['surface']} !important;
    border: 1px solid {THEME['border']} !important;
    border-radius: 12px !important; margin-bottom: 6px !important;
}}
[data-testid="stExpander"] summary {{
    color: {THEME['text']} !important; font-size: 14px !important;
    font-weight: 500 !important;
}}

/* ── selectbox & slider ── */
[data-testid="stSelectbox"] > div > div,
.stSlider {{ color: {THEME['text']} !important; }}

/* ── agent pill ── */
.agent-pill {{
    display: inline-flex; align-items: center; gap: 6px;
    background: {THEME['surface2']}; border: 1px solid {THEME['border']};
    border-radius: 20px; padding: 4px 12px;
    font-size: 12px; font-weight: 500; color: {THEME['text_muted']};
    margin-bottom: 12px;
}}
.agent-pill-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: {THEME['accent3']};
    box-shadow: 0 0 6px {THEME['accent3']};
}}

/* ── empty state ── */
.empty-state {{
    text-align: center; padding: 60px 20px; color: {THEME['text_muted']};
}}
.empty-state-icon {{ font-size: 48px; margin-bottom: 12px; opacity: 0.4; }}
.empty-state-text {{ font-size: 15px; font-weight: 500; margin-bottom: 6px; }}
.empty-state-sub  {{ font-size: 13px; opacity: 0.7; }}

/* ── file chip ── */
.file-chip {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(79,142,247,0.1); border: 1px solid rgba(79,142,247,0.2);
    border-radius: 20px; padding: 3px 10px 3px 8px;
    font-size: 12px; color: {THEME['accent']}; margin: 2px;
}}

/* ── interview timeline ── */
.timeline-item {{
    display: flex; gap: 16px; margin-bottom: 16px;
}}
.timeline-dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: {THEME['accent']}; margin-top: 4px; flex-shrink: 0;
    box-shadow: 0 0 8px {THEME['accent']}80;
}}
.timeline-line {{
    width: 1px; background: {THEME['border']}; margin: 14px 0 0 4px;
    flex-shrink: 0;
}}

/* ── scrollbar ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: {THEME['border']}; border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{ background: {THEME['text_muted']}; }}

/* ── stMarkdown fix ── */
.stMarkdown p {{ margin: 0; }}

/* sidebar selectbox */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
    background: {THEME['surface2']} !important;
    border: 1px solid {THEME['border']} !important;
    border-radius: 8px !important;
    color: {THEME['text']} !important;
}}
</style>
""", unsafe_allow_html=True)


# ── session state ─────────────────────────────────────────────────────────────
def _init_state():
    for k, v in {
        "page":             "chat",
        "active_agent":     "main",
        "chat_history":     {},
        "agents":           {},
        "kb_files":         [],
        "search_results":   [],
        "search_query":     "",
        "user_id":          os.getenv("TASK_AGENT_USER", "local-user"),
        "pending_approval": None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── agent loaders ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _load_main_agent(uid):
    from productive_agent.agents.orchestrator import build_main_agent
    from productive_agent.agents.task_agent import init_db
    init_db(); return build_main_agent(user_id=uid)

@st.cache_resource(show_spinner=False)
def _load_email_agent(uid):
    from productive_agent.agents.email_agent import build_agent
    return build_agent(user_id=uid)

@st.cache_resource(show_spinner=False)
def _load_task_agent(uid):
    from productive_agent.agents.task_agent import build_agent, init_db
    init_db(); return build_agent(user_id=uid)

@st.cache_resource(show_spinner=False)
def _load_interview_agent(uid):
    from productive_agent.agents.interview_agent import build_agent
    from productive_agent.agents.task_agent import init_db
    init_db(); return build_agent(user_id=uid)

def _load_knowledge_agent(fps, uid):
    from productive_agent.agents.knowledge_agent import build_agent
    return build_agent(fps, user_id=uid)


def get_agent_entry(key: str):
    if key in st.session_state.agents:
        return st.session_state.agents[key]
    uid = st.session_state.user_id

    if key == "main":
        agent = _load_main_agent(uid)
        if st.session_state.kb_files:
            from productive_agent.agents.orchestrator import build_main_agent
            from productive_agent.agents.task_agent import init_db
            init_db()
            agent = build_main_agent(user_id=uid, kb_files=st.session_state.kb_files)
        entry = {"agent": agent, "config": {"configurable": {"thread_id": f"main-{uid}"}}, "context": None}
    elif key == "email":
        entry = {"agent": _load_email_agent(uid), "config": {"configurable": {"thread_id": f"email-{uid}"}}, "context": None}
    elif key == "task":
        from productive_agent.agents.task_agent import Context
        entry = {"agent": _load_task_agent(uid), "config": {"configurable": {"thread_id": f"task-{uid}"}}, "context": Context(user_id=uid)}
    elif key == "interview":
        from productive_agent.agents.interview_agent import Context
        entry = {"agent": _load_interview_agent(uid), "config": {"configurable": {"thread_id": f"interview-{uid}"}}, "context": Context(user_id=uid)}
    elif key == "knowledge":
        if not st.session_state.kb_files:
            return None
        entry = {"agent": _load_knowledge_agent(st.session_state.kb_files, uid), "config": {"configurable": {"thread_id": "knowledge-1"}}, "context": None}
    else:
        return None

    st.session_state.agents[key] = entry
    return entry


def invoke_agent(key: str, user_input: str) -> str:
    entry = get_agent_entry(key)
    if not entry:
        return "⚠️ Agent not ready. Upload files first."
    try:
        payload = {"messages": [{"role": "user", "content": user_input}]}
        result = (entry["agent"].invoke(payload, config=entry["config"], context=entry["context"])
                  if entry["context"] else
                  entry["agent"].invoke(payload, config=entry["config"]))
        content = result["messages"][-1].content
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))

        if isinstance(content, str) and content.startswith("APPROVAL_REQUIRED|"):
            parts = content.split("|", 3)
            st.session_state["pending_approval"] = {
                "agent_key": key,
                "action":    parts[1] if len(parts) > 1 else "",
                "item_id":   parts[2] if len(parts) > 2 else "",
                "preview":   parts[3] if len(parts) > 3 else "",
            }
            label = "send this email" if parts[1] == "send_email" else "delete this task"
            return f"⚡ **Action required** — I need your approval to {label}. See the card below."

        try:
            from productive_agent.core.memory import MemoryStore
            MemoryStore(st.session_state.user_id).save_summary(key, content[:120])
        except Exception:
            pass
        return content
    except Exception as e:
        return f"❌ Error: {e}"


# ── DB helpers ────────────────────────────────────────────────────────────────
def _db_path():
    p = os.environ.get("TASK_DB_PATH", str(ROOT / "data" / "tasks.db"))
    return p if Path(p).exists() else str(AGENT_DIR / "tasks.db")

def fetch_tasks(status="open", days_ahead=14):
    dp = _db_path()
    if not Path(dp).exists():
        return []
    uid = st.session_state.user_id
    conn = sqlite3.connect(dp); conn.row_factory = sqlite3.Row
    w, p = ["user_id = ?"], [uid]
    if status == "open":   w.append("status IN ('todo','in_progress')")
    elif status != "all":  w.append("status = ?"); p.append(status)
    cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
    w.append("(due_date IS NULL OR substr(due_date,1,10) <= ?)"); p.append(cutoff)
    rows = conn.execute(f"SELECT * FROM tasks WHERE {' AND '.join(w)} ORDER BY due_date,priority", p).fetchall()
    conn.close(); return [dict(r) for r in rows]

def fetch_task_stats():
    dp = _db_path()
    if not Path(dp).exists():
        return {}
    uid = st.session_state.user_id
    conn = sqlite3.connect(dp); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT status, COUNT(*) as c FROM tasks WHERE user_id=? GROUP BY status", (uid,)).fetchall()
    conn.close(); return {r["status"]: r["c"] for r in rows}

def fetch_interview_tasks():
    dp = _db_path()
    if not Path(dp).exists():
        return []
    uid = st.session_state.user_id
    conn = sqlite3.connect(dp); conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? "
        "AND (title LIKE '%Study:%' OR title LIKE '%interview%' OR title LIKE '%Review%' OR title LIKE '%Mock%') "
        "AND status != 'done' ORDER BY due_date", (uid,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def do_web_search(q):
    try:
        from tavily import TavilyClient
        return TavilyClient().search(q, max_results=6).get("results", [])
    except Exception as e:
        return [{"title": "Error", "content": str(e), "url": ""}]


# ── sidebar ───────────────────────────────────────────────────────────────────
PAGES = [
    ("✦", "💬 Chat",             "chat"),
    ("✦", "📅 Tasks",            "tasks"),
    ("✦", "🎯 Interview Plan",   "interview_plan"),
    ("✦", "🔍 Web Search",       "web_search"),
    ("✦", "📚 Knowledge Base",   "knowledge"),
]
AGENT_OPTS = {
    "🤖 Auto (Main Agent)": "main",
    "📧 Email":             "email",
    "✅ Tasks":             "task",
    "🎯 Interview Prep":    "interview",
    "📚 Knowledge":         "knowledge",
}

def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
            <div class="sidebar-logo-icon">✦</div>
            <div>
                <div class="sidebar-logo-text">Productive Agent</div>
                <div class="sidebar-logo-sub">AI-powered workspace</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Nav
        st.markdown('<div class="nav-section-label">Navigation</div>', unsafe_allow_html=True)
        for _, label, pg in PAGES:
            is_active = st.session_state.page == pg
            css_class = "nav-active" if is_active else ""
            with st.container():
                st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                if st.button(label, key=f"nav_{pg}", use_container_width=True):
                    st.session_state.page = pg; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Agent selector
        if st.session_state.page == "chat":
            st.markdown('<div class="nav-section-label" style="margin-top:20px">Active Agent</div>', unsafe_allow_html=True)
            cur_label = next((l for l, k in AGENT_OPTS.items() if k == st.session_state.active_agent), list(AGENT_OPTS.keys())[0])
            chosen = st.selectbox("agent", list(AGENT_OPTS.keys()),
                                  index=list(AGENT_OPTS.keys()).index(cur_label),
                                  label_visibility="collapsed")
            new_key = AGENT_OPTS[chosen]
            if new_key != st.session_state.active_agent:
                st.session_state.active_agent = new_key; st.rerun()

        # KB uploader
        st.markdown('<div class="nav-section-label" style="margin-top:20px">📂 Knowledge Base</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#7d8fa9;margin-bottom:8px">Upload files to chat with them</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop files here (PDF, DOCX, TXT…)",
            type=["pdf","docx","txt","md","csv","py"],
            accept_multiple_files=True,
            help="Supported: PDF, Word, Text, Markdown, CSV, Python"
        )
        if uploaded:
            tmp = ROOT / ".kb_uploads"; tmp.mkdir(exist_ok=True)
            saved = []
            for f in uploaded:
                d = tmp / f.name; d.write_bytes(f.read()); saved.append(str(d))
            if set(saved) != set(st.session_state.kb_files):
                st.session_state.kb_files = saved
                st.session_state.agents.pop("knowledge", None)
        if st.session_state.kb_files:
            for fp in st.session_state.kb_files:
                st.markdown(f'<div class="file-chip">📄 {Path(fp).name}</div>', unsafe_allow_html=True)

        # Footer
        st.markdown(f"""
        <div style="position:absolute;bottom:20px;left:16px;right:16px;">
            <div style="font-size:11px;color:{THEME['text_muted']};border-top:1px solid {THEME['border']};padding-top:12px;">
                <div style="margin-bottom:4px;">⚡ {os.getenv('AGENT_MODEL','gpt-5-nano')}</div>
                <div>👤 {st.session_state.user_id}</div>
            </div>
        </div>""", unsafe_allow_html=True)


# ── approval widget ───────────────────────────────────────────────────────────
def render_approval_widget():
    a = st.session_state.get("pending_approval")
    if not a: return
    action, item_id, preview, agent_key = a["action"], a["item_id"], a["preview"], a["agent_key"]
    title  = "📤 Send Email"   if action == "send_email" else "🗑️ Delete Task"
    c_lbl  = "Send Email"      if action == "send_email" else "Delete Task"

    st.markdown(f"""
    <div class="approval-card">
        <div class="approval-title">⚡ {title} — Approval Required</div>
        <div class="approval-preview">{preview[:600]}</div>
    </div>""", unsafe_allow_html=True)

    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button(f"✅ {c_lbl}", key="appr_ok", type="primary"):
        if action == "send_email":
            from productive_agent.tools.gmail import _send_draft_execute
            msg = _send_draft_execute(item_id)
        else:
            from productive_agent.agents.task_agent import _delete_task_execute
            msg = _delete_task_execute(st.session_state.user_id, int(item_id))
        h = st.session_state.chat_history.get(agent_key, [])
        h.append({"role": "assistant", "content": f"✅ {msg}"})
        st.session_state.chat_history[agent_key] = h
        st.session_state["pending_approval"] = None; st.rerun()
    if c2.button("❌ Cancel", key="appr_cancel"):
        h = st.session_state.chat_history.get(agent_key, [])
        h.append({"role": "assistant", "content": "Action cancelled."})
        st.session_state.chat_history[agent_key] = h
        st.session_state["pending_approval"] = None; st.rerun()


# ── chat page ─────────────────────────────────────────────────────────────────
AGENT_META = {
    "main":      ("🤖", "Main Agent",         "bg:#4f8ef7"),
    "email":     ("📧", "Email Agent",        "bg:#a78bfa"),
    "task":      ("✅", "Task Agent",          "bg:#34d399"),
    "interview": ("🎯", "Interview Prep",     "bg:#fb923c"),
    "knowledge": ("📚", "Knowledge Search",   "bg:#e879f9"),
}

def render_chat():
    key = st.session_state.active_agent
    icon, name, _ = AGENT_META.get(key, ("🤖", "Agent", ""))

    if key == "knowledge" and not st.session_state.kb_files:
        st.markdown(f"""
        <div class="page-header">
            <div class="page-header-icon" style="background:rgba(232,121,249,0.15)">📚</div>
            <div>
                <div class="page-header-title">Knowledge Search</div>
                <div class="page-header-sub">Chat with your documents</div>
            </div>
        </div>
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div class="empty-state-text">No files loaded</div>
            <div class="empty-state-sub">Upload PDF, DOCX, or TXT files using the sidebar</div>
        </div>""", unsafe_allow_html=True); return

    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon" style="background:rgba(79,142,247,0.12)">{icon}</div>
        <div>
            <div class="page-header-title">{name}</div>
            <div class="page-header-sub">Ask anything — I'll figure out the rest</div>
        </div>
    </div>""", unsafe_allow_html=True)

    history = st.session_state.chat_history.get(key, [])
    chat_box = st.container(height=500, border=False)

    with chat_box:
        if not history:
            hints = {
                "main":      ("I have an interview Thursday, build me a study plan", "show me my tasks for this week"),
                "email":     ("show my latest job emails", "search for interview invitations"),
                "task":      ("show my open tasks", "what's free tomorrow?"),
                "interview": ("scan my emails for interviews", "prepare me for my next interview"),
                "knowledge": ("summarize this document", "what does it say about X?"),
            }
            h1, h2 = hints.get(key, ("", ""))
            st.markdown(f"""
            <div style="text-align:center;padding:40px 20px;">
                <div style="font-size:36px;margin-bottom:12px">{icon}</div>
                <div style="font-size:16px;font-weight:600;color:{THEME['text']};margin-bottom:6px">
                    Hello! How can I help?
                </div>
                <div style="font-size:13px;color:{THEME['text_muted']};margin-bottom:24px">
                    Try one of these to get started
                </div>
                <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
                    <span style="background:{THEME['surface2']};border:1px solid {THEME['border']};
                          border-radius:20px;padding:6px 14px;font-size:12px;color:{THEME['text_muted']}">
                        💬 {h1}
                    </span>
                    <span style="background:{THEME['surface2']};border:1px solid {THEME['border']};
                          border-radius:20px;padding:6px 14px;font-size:12px;color:{THEME['text_muted']}">
                        💬 {h2}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            for msg in history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="msg-row-user"><div class="bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    content = msg["content"]
                    # basic markdown-ish render
                    content = content.replace("\n", "<br>")
                    st.markdown(f'<div class="msg-row-agent"><div class="bubble-agent">{content}</div></div>', unsafe_allow_html=True)

    # Approval widget inside chat
    render_approval_widget()

    # Input row — file uploader + text input + send button
    # File uploader must be outside the form (Streamlit limitation)
    inp_col, upload_col = st.columns([10, 1])

    with upload_col:
        st.markdown('<div style="padding-top:4px">', unsafe_allow_html=True)
        new_files = st.file_uploader(
            "📎",
            type=["pdf","docx","txt","md","csv","py"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Upload files to Knowledge Base",
            key=f"uploader_{key}",
        )
        st.markdown('</div>', unsafe_allow_html=True)
        if new_files:
            tmp = ROOT / ".kb_uploads"; tmp.mkdir(exist_ok=True)
            saved = []
            for f in new_files:
                d = tmp / f.name; d.write_bytes(f.read()); saved.append(str(d))
            if set(saved) != set(st.session_state.kb_files):
                st.session_state.kb_files = saved
                st.session_state.agents.pop("knowledge", None)
                st.success(f"✅ {len(saved)} file(s) loaded — switch to Knowledge agent to chat with them")

    with inp_col:
        with st.form(key=f"chat_{key}", clear_on_submit=True):
            c1, c2 = st.columns([10, 1])
            user_input = c1.text_input("msg", placeholder=f"Message {name}…", label_visibility="collapsed")
            send = c2.form_submit_button("↑", use_container_width=True)
    if send and user_input.strip():
        msg = user_input.strip()
        history.append({"role": "user", "content": msg})
        st.session_state.chat_history[key] = history
        with st.spinner(""):
            reply = invoke_agent(key, msg)
        history.append({"role": "assistant", "content": reply})
        st.session_state.chat_history[key] = history
        st.rerun()

    if history:
        if st.button("Clear", key=f"clr_{key}", help="Clear conversation"):
            st.session_state.chat_history[key] = []; st.rerun()


# ── tasks page ────────────────────────────────────────────────────────────────
def render_tasks():
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon" style="background:rgba(52,211,153,0.12)">📅</div>
        <div>
            <div class="page-header-title">Tasks & Calendar</div>
            <div class="page-header-sub">Your schedule at a glance</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Stats row
    stats = fetch_task_stats()
    todo  = stats.get("todo", 0)
    wip   = stats.get("in_progress", 0)
    done  = stats.get("done", 0)
    total = todo + wip + done
    s1, s2, s3, s4 = st.columns(4)
    for col, num, lbl in [(s1, total, "Total"), (s2, todo, "To Do"),
                           (s3, wip, "In Progress"), (s4, done, "Done")]:
        col.markdown(f'<div class="stat-card"><div class="stat-number">{num}</div><div class="stat-label">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filters
    fc, dc, _, rc = st.columns([2, 2, 3, 1])
    status_filter = fc.selectbox("Status", ["open","todo","in_progress","done","all"], label_visibility="collapsed")
    days_ahead    = dc.slider("Days", 1, 60, 14, label_visibility="collapsed")
    if rc.button("↺", help="Refresh"):
        st.rerun()

    tasks = fetch_tasks(status_filter, days_ahead)
    if not tasks:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">✅</div>
            <div class="empty-state-text">No tasks found</div>
            <div class="empty-state-sub">Use the Task Agent to create tasks</div>
        </div>""", unsafe_allow_html=True); return

    groups: dict[str, list] = {}
    for t in tasks:
        groups.setdefault((t.get("due_date") or "No due date")[:10], []).append(t)

    today_s    = date.today().isoformat()
    tomorrow_s = (date.today() + timedelta(days=1)).isoformat()

    for day in sorted(groups.keys()):
        items = groups[day]
        is_today = day == today_s
        day_label = ("📌 Today" if is_today else
                     "⏰ Tomorrow" if day == tomorrow_s else
                     "📋 No due date" if day == "No due date" else
                     datetime.strptime(day, "%Y-%m-%d").strftime("📆 %a, %b %d") if day != "No due date" else day)
        day_cls = "day-today" if is_today else ""

        st.markdown(f"""
        <div class="day-label {day_cls}">
            {day_label}
            <span class="day-count">{len(items)}</span>
        </div>""", unsafe_allow_html=True)

        for t in items:
            pri   = t.get("priority", "medium")
            sts   = t.get("status", "todo")
            due   = t["due_date"][:10] if t.get("due_date") else ""
            st.markdown(f"""
            <div class="task-card {pri}">
                <div class="task-title">#{t['id']} {t['title']}</div>
                <div class="task-badges">
                    <span class="badge badge-{sts}">{sts.replace('_',' ')}</span>
                    <span class="badge badge-{pri}">{pri}</span>
                    {"<span class='task-due'>📅 "+due+"</span>" if due else ""}
                </div>
                {"<div class='task-desc'>"+t['description']+"</div>" if t.get('description') else ""}
            </div>""", unsafe_allow_html=True)


# ── interview plan page ───────────────────────────────────────────────────────
def render_interview_plan():
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon" style="background:rgba(251,146,60,0.12)">🎯</div>
        <div>
            <div class="page-header-title">Interview Prep Plan</div>
            <div class="page-header-sub">Your study timeline</div>
        </div>
    </div>""", unsafe_allow_html=True)

    _, rc = st.columns([5, 1])
    if rc.button("↺ Refresh"): st.rerun()

    tasks = fetch_interview_tasks()
    if not tasks:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">🎯</div>
            <div class="empty-state-text">No prep plan yet</div>
            <div class="empty-state-sub">Go to Chat → Interview Prep and say<br>"scan my emails for interviews"</div>
        </div>""", unsafe_allow_html=True)
    else:
        groups: dict[str, list] = {}
        for t in tasks:
            groups.setdefault((t.get("due_date") or "Unscheduled")[:10], []).append(t)

        max_day = max((d for d in groups if d != "Unscheduled"), default=None)
        if max_day:
            days_left = (date.fromisoformat(max_day) - date.today()).days
            if days_left > 0:
                st.markdown(f"""
                <div style="background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);
                            border-radius:12px;padding:14px 18px;margin-bottom:20px;
                            font-size:14px;color:{THEME['success']}">
                    🗓 Interview in <strong>{days_left} day(s)</strong> — {max_day}
                </div>""", unsafe_allow_html=True)
            elif days_left == 0:
                st.markdown(f'<div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;color:{THEME["warning"]}">🚨 Interview is <strong>today</strong>! Good luck!</div>', unsafe_allow_html=True)

        # Timeline
        for day in sorted(groups.keys()):
            try:   label = datetime.strptime(day, "%Y-%m-%d").strftime("%A, %B %d")
            except: label = day
            st.markdown(f'<div class="day-label">{label}</div>', unsafe_allow_html=True)
            for t in groups[day]:
                pri   = t.get("priority", "medium")
                color = {"high": THEME["danger"], "medium": THEME["warning"], "low": THEME["success"]}.get(pri, THEME["text_muted"])
                st.markdown(f"""
                <div class="task-card {pri}" style="padding-left:20px">
                    <div class="timeline-dot" style="float:left;margin:-2px 12px 0 -16px;background:{color};box-shadow:0 0 8px {color}80"></div>
                    <div class="task-title" style="color:{color}">📖 {t['title']}</div>
                    {"<div class='task-desc'>"+t['description']+"</div>" if t.get('description') else ""}
                </div>""", unsafe_allow_html=True)

    # Quick chat
    st.markdown(f'<div class="day-label" style="margin-top:24px">💬 Quick Question</div>', unsafe_allow_html=True)
    with st.form("ivc"):
        c1, c2 = st.columns([9, 1])
        q = c1.text_input("q", placeholder="What should I focus on today?", label_visibility="collapsed")
        if c2.form_submit_button("↑", use_container_width=True) and q.strip():
            with st.spinner(""):
                reply = invoke_agent("interview", q.strip())
            st.markdown(f'<div class="bubble-agent" style="margin-top:10px">{reply}</div>', unsafe_allow_html=True)


# ── web search page ───────────────────────────────────────────────────────────
def render_web_search():
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon" style="background:rgba(79,142,247,0.12)">🔍</div>
        <div>
            <div class="page-header-title">Web Search</div>
            <div class="page-header-sub">Search the web and send results to any agent</div>
        </div>
    </div>""", unsafe_allow_html=True)

    with st.form("sf"):
        c1, c2 = st.columns([9, 1])
        q = c1.text_input("q", placeholder="Search anything…",
                          value=st.session_state.search_query, label_visibility="collapsed")
        if c2.form_submit_button("↑", use_container_width=True) and q.strip():
            st.session_state.search_query = q.strip()
            with st.spinner("Searching…"):
                st.session_state.search_results = do_web_search(q.strip())

    results = st.session_state.search_results
    if results:
        st.markdown(f'<div class="day-label">{len(results)} results for "{st.session_state.search_query}"</div>', unsafe_allow_html=True)
        for r in results:
            title   = r.get("title", "No title")
            snippet = r.get("content", r.get("snippet", ""))[:280]
            url     = r.get("url", "")
            st.markdown(f"""
            <div class="search-card">
                <div class="search-card-title"><a href="{url}" target="_blank" style="color:inherit;text-decoration:none">{title} ↗</a></div>
                <div class="search-card-snippet">{snippet}{"…" if len(snippet)==280 else ""}</div>
                <div class="search-card-url">{url[:80]}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f'<div class="day-label" style="margin-top:20px">💬 Send to Agent</div>', unsafe_allow_html=True)
        with st.form("saf"):
            ac, qc, bc = st.columns([2, 5, 1])
            ag = ac.selectbox("ag", list(AGENT_OPTS.values()), format_func=lambda x: next((l for l,k in AGENT_OPTS.items() if k==x),x), label_visibility="collapsed")
            fq = qc.text_input("fq", placeholder="Ask something about these results…", label_visibility="collapsed")
            if bc.form_submit_button("↑", use_container_width=True) and fq.strip():
                ctx = (f"Web search results for '{st.session_state.search_query}':\n\n" +
                       "\n\n".join(f"- {r.get('title','')}: {r.get('content','')[:180]}" for r in results[:4]) +
                       f"\n\nQuestion: {fq.strip()}")
                with st.spinner(""):
                    reply = invoke_agent(ag, ctx)
                st.markdown(f'<div class="bubble-agent" style="margin-top:12px">{reply}</div>', unsafe_allow_html=True)


# ── knowledge page ────────────────────────────────────────────────────────────
def render_knowledge():
    st.markdown(f"""
    <div class="page-header">
        <div class="page-header-icon" style="background:rgba(232,121,249,0.12)">📚</div>
        <div>
            <div class="page-header-title">Knowledge Base</div>
            <div class="page-header-sub">Chat with your uploaded documents</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.kb_files:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div class="empty-state-text">No documents loaded</div>
            <div class="empty-state-sub">Upload files below or using the sidebar uploader</div>
        </div>""", unsafe_allow_html=True)

        # Show uploader inline on the page too
        inline_uploaded = st.file_uploader(
            "📎 Upload your files here",
            type=["pdf","docx","txt","md","csv","py"],
            accept_multiple_files=True,
            help="Supported: PDF, Word, Text, Markdown, CSV, Python"
        )
        if inline_uploaded:
            tmp = ROOT / ".kb_uploads"; tmp.mkdir(exist_ok=True)
            saved = []
            for f in inline_uploaded:
                d = tmp / f.name; d.write_bytes(f.read()); saved.append(str(d))
            st.session_state.kb_files = saved
            st.session_state.agents.pop("knowledge", None)
            st.rerun()
        return

    st.markdown(f'<div style="margin-bottom:12px">' +
                "".join(f'<div class="file-chip">📄 {Path(fp).name}</div>' for fp in st.session_state.kb_files) +
                "</div>", unsafe_allow_html=True)

    history = st.session_state.chat_history.get("knowledge", [])
    kb_box  = st.container(height=420, border=False)
    with kb_box:
        if not history:
            st.markdown(f"""
            <div style="text-align:center;padding:40px 0;color:{THEME['text_muted']}">
                📚 Ask anything about your documents
            </div>""", unsafe_allow_html=True)
        for msg in history:
            if msg["role"] == "user":
                st.markdown(f'<div class="msg-row-user"><div class="bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-row-agent"><div class="bubble-agent">{msg["content"].replace(chr(10),"<br>")}</div></div>', unsafe_allow_html=True)

    with st.form("kbf", clear_on_submit=True):
        c1, c2 = st.columns([9, 1])
        ui = c1.text_input("kb", placeholder="Ask about your documents…", label_visibility="collapsed")
        if c2.form_submit_button("↑", use_container_width=True) and ui.strip():
            history.append({"role": "user", "content": ui.strip()})
            st.session_state.chat_history["knowledge"] = history
            with st.spinner(""):
                reply = invoke_agent("knowledge", ui.strip())
            history.append({"role": "assistant", "content": reply})
            st.session_state.chat_history["knowledge"] = history
            st.rerun()


# ── router ────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    {
        "chat":           render_chat,
        "tasks":          render_tasks,
        "interview_plan": render_interview_plan,
        "web_search":     render_web_search,
        "knowledge":      render_knowledge,
    }.get(st.session_state.page, render_chat)()


main()
