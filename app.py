"""
Productive Agent — Streamlit UI
================================
Run:  streamlit run app.py
"""

import os
import sys
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

# ── path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
AGENT_DIR = ROOT / "agent"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(AGENT_DIR))   # keep for any legacy imports

os.environ.setdefault("TASK_DB_PATH", str(ROOT / "data" / "tasks.db"))
os.environ.setdefault("USER_PREFS_PATH", str(ROOT / "data" / "user_preferences.json"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import streamlit as st

# ── page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Productive Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── global ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    border: 1px solid #334155;
    color: #e2e8f0 !important;
    border-radius: 8px;
    margin-bottom: 6px;
    text-align: left;
    padding: 10px 14px;
    font-size: 14px;
    transition: all 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #334155;
    border-color: #6366f1;
}

/* ── chat bubbles ── */
.bubble-user {
    background: #6366f1;
    color: white;
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0 8px 20%;
    word-wrap: break-word;
    font-size: 14px;
}
.bubble-ai {
    background: #1e293b;
    color: #e2e8f0;
    padding: 12px 16px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 20% 8px 0;
    word-wrap: break-word;
    font-size: 14px;
    border: 1px solid #334155;
}
.bubble-label {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 2px;
}

/* ── task cards ── */
.task-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.task-card.high   { border-left: 4px solid #ef4444; }
.task-card.medium { border-left: 4px solid #f59e0b; }
.task-card.low    { border-left: 4px solid #22c55e; }
.task-title { font-weight: 600; color: #f1f5f9; font-size: 14px; }
.task-meta  { font-size: 12px; color: #94a3b8; margin-top: 4px; }

/* ── search result ── */
.search-result {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 10px;
}
.search-title { font-weight: 600; color: #818cf8; font-size: 14px; }
.search-snippet { font-size: 13px; color: #cbd5e1; margin-top: 6px; }
.search-url { font-size: 11px; color: #64748b; margin-top: 4px; }

/* ── section headers ── */
.section-header {
    font-size: 20px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #334155;
}
</style>
""", unsafe_allow_html=True)


# ── session state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "page": "chat",
        "active_agent": "main",   # default to main orchestrator
        "chat_history": {},
        "agents": {},
        "kb_files": [],
        "search_results": [],
        "search_query": "",
        "user_id": os.getenv("TASK_AGENT_USER", "local-user"),
        "pending_approval": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── agent loader ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading agent…")
def _load_main_agent(user_id: str):
    from productive_agent.agents.orchestrator import build_main_agent
    from productive_agent.agents.task_agent import init_db
    init_db()
    return build_main_agent(user_id=user_id)

@st.cache_resource(show_spinner="Loading agent…")
def _load_email_agent(user_id: str):
    from productive_agent.agents.email_agent import build_agent
    return build_agent(user_id=user_id)

@st.cache_resource(show_spinner="Loading agent…")
def _load_task_agent(user_id: str):
    from productive_agent.agents.task_agent import build_agent, init_db
    init_db()
    return build_agent(user_id=user_id)

@st.cache_resource(show_spinner="Loading agent…")
def _load_interview_agent(user_id: str):
    from productive_agent.agents.interview_agent import build_agent
    from productive_agent.agents.task_agent import init_db
    init_db()
    return build_agent(user_id=user_id)

def _load_knowledge_agent(file_paths: list[str], user_id: str):
    from productive_agent.agents.knowledge_agent import build_agent
    return build_agent(file_paths, user_id=user_id)


def get_agent_entry(key: str):
    """Return or lazily build the agent entry dict."""
    if key in st.session_state.agents:
        return st.session_state.agents[key]

    uid = st.session_state.user_id

    if key == "main":
        agent = _load_main_agent(uid)
        # Pass kb_files so the main agent can use knowledge_agent if files are loaded
        # Rebuild if kb_files changed
        if st.session_state.kb_files:
            from main_agent import build_main_agent
            from task_agent import init_db
            init_db()
            agent = build_main_agent(user_id=uid, kb_files=st.session_state.kb_files)
        entry = {"agent": agent,
                 "config": {"configurable": {"thread_id": f"main-{uid}"}},
                 "context": None}

    elif key == "email":
        agent = _load_email_agent(uid)
        entry = {"agent": agent,
                 "config": {"configurable": {"thread_id": f"email-{uid}"}},
                 "context": None}

    elif key == "task":
        from productive_agent.agents.task_agent import Context
        agent = _load_task_agent(uid)
        entry = {"agent": agent,
                 "config": {"configurable": {"thread_id": f"task-{uid}"}},
                 "context": Context(user_id=uid)}

    elif key == "interview":
        from productive_agent.agents.interview_agent import Context
        agent = _load_interview_agent(uid)
        entry = {"agent": agent,
                 "config": {"configurable": {"thread_id": f"interview-{uid}"}},
                 "context": Context(user_id=uid)}

    elif key == "knowledge":
        if not st.session_state.kb_files:
            return None
        agent = _load_knowledge_agent(st.session_state.kb_files, uid)
        entry = {"agent": agent,
                 "config": {"configurable": {"thread_id": "knowledge-1"}},
                 "context": None}
    else:
        return None

    st.session_state.agents[key] = entry
    return entry


def invoke_agent(key: str, user_input: str) -> str:
    entry = get_agent_entry(key)
    if entry is None:
        return "⚠️ Agent not ready. Please load files first."
    agent   = entry["agent"]
    config  = entry["config"]
    context = entry["context"]
    payload = {"messages": [{"role": "user", "content": user_input}]}
    try:
        if context is not None:
            result = agent.invoke(payload, config=config, context=context)
        else:
            result = agent.invoke(payload, config=config)
        content = result["messages"][-1].content
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))

        # ── HITL sentinel detection ──────────────────────────────────────
        # Format: APPROVAL_REQUIRED|<action>|<id>|<preview>
        if isinstance(content, str) and content.startswith("APPROVAL_REQUIRED|"):
            parts = content.split("|", 3)
            action  = parts[1] if len(parts) > 1 else "unknown"
            item_id = parts[2] if len(parts) > 2 else ""
            preview = parts[3] if len(parts) > 3 else ""
            st.session_state["pending_approval"] = {
                "agent_key": key,
                "action":    action,
                "item_id":   item_id,
                "preview":   preview,
            }
            # Return a user-visible message (not the raw sentinel)
            label = "send this email" if action == "send_email" else "delete this task"
            return f"⏳ **Approval required** — I want to {label}. See the confirmation below."

        # ── Save a one-line summary to long-term memory ──────────────────
        try:
            from productive_agent.core.memory import MemoryStore
            uid = st.session_state.get("user_id", "local-user")
            mem = MemoryStore(uid)
            short_summary = (content[:120] + "…") if len(content) > 120 else content
            mem.save_summary(agent=key, summary=short_summary)
        except Exception:
            pass  # never let memory errors break the chat

        return content
    except Exception as e:
        return f"❌ Error: {e}"


def render_approval_widget():
    """Render the confirmation card when a pending approval exists."""
    approval = st.session_state.get("pending_approval")
    if not approval:
        return

    action  = approval["action"]
    item_id = approval["item_id"]
    preview = approval["preview"]

    if action == "send_email":
        title = "📤 Send Email — Approval Required"
        confirm_label = "✅ Send Email"
    else:
        title = "🗑 Delete Task — Approval Required"
        confirm_label = "🗑 Delete Task"

    st.markdown("---")
    with st.container():
        st.warning(f"**{title}**")
        st.code(preview, language=None)
        col1, col2 = st.columns(2)

        if col1.button(confirm_label, key="approval_confirm", type="primary"):
            # Execute the approved action
            if action == "send_email":
                from productive_agent.tools.gmail import _send_draft_execute
                result_msg = _send_draft_execute(item_id)
            else:
                from productive_agent.agents.task_agent import _delete_task_execute
                uid = st.session_state.get("user_id", "local-user")
                result_msg = _delete_task_execute(uid, int(item_id))

            st.session_state["pending_approval"] = None
            # Add result to chat history
            key = approval["agent_key"]
            history = st.session_state.chat_history.get(key, [])
            history.append({"role": "assistant", "content": f"✅ {result_msg}"})
            st.session_state.chat_history[key] = history
            st.rerun()

        if col2.button("❌ Cancel", key="approval_cancel"):
            key = approval["agent_key"]
            history = st.session_state.chat_history.get(key, [])
            history.append({"role": "assistant", "content": "Action cancelled."})
            st.session_state.chat_history[key] = history
            st.session_state["pending_approval"] = None
            st.rerun()


# ── DB helpers ────────────────────────────────────────────────────────────────
def fetch_tasks(status_filter="open", days_ahead=14):
    db_path = os.environ.get("TASK_DB_PATH", str(AGENT_DIR / "tasks.db"))
    if not Path(db_path).exists():
        return []
    uid = st.session_state.user_id
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    where = ["user_id = ?"]
    params = [uid]
    if status_filter == "open":
        where.append("status IN ('todo','in_progress')")
    elif status_filter != "all":
        where.append("status = ?")
        params.append(status_filter)
    cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
    where.append("(due_date IS NULL OR substr(due_date,1,10) <= ?)")
    params.append(cutoff)
    rows = conn.execute(
        f"SELECT * FROM tasks WHERE {' AND '.join(where)} ORDER BY due_date, priority",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_interview_tasks():
    db_path = os.environ.get("TASK_DB_PATH", str(AGENT_DIR / "tasks.db"))
    if not Path(db_path).exists():
        return []
    uid = st.session_state.user_id
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? "
        "AND (title LIKE '%Study:%' OR title LIKE '%interview%' "
        "     OR title LIKE '%Review%' OR title LIKE '%Mock%') "
        "AND status != 'done' ORDER BY due_date",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── web search helper ─────────────────────────────────────────────────────────
def do_web_search(query: str) -> list[dict]:
    try:
        from tavily import TavilyClient
        client = TavilyClient()
        res = client.search(query, max_results=6)
        return res.get("results", [])
    except Exception as e:
        return [{"title": "Error", "content": str(e), "url": ""}]


# ── sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🤖 Productive Agent")
        st.markdown("---")

        # Navigation
        st.markdown("**Navigation**")
        pages = [
            ("💬 Chat",              "chat"),
            ("📅 Tasks & Calendar",  "tasks"),
            ("🎯 Interview Plan",    "interview_plan"),
            ("🔍 Web Search",        "web_search"),
            ("📂 Knowledge Base",    "knowledge"),
        ]
        for label, page_key in pages:
            active = st.session_state.page == page_key
            btn_label = f"**{label}**" if active else label
            if st.button(btn_label, key=f"nav_{page_key}"):
                st.session_state.page = page_key
                st.rerun()

        st.markdown("---")

        # Active agent selector (only on chat page)
        if st.session_state.page == "chat":
            st.markdown("**Active Agent**")
            agent_options = {
                "🤖 Main Agent (Auto)":    "main",
                "📧 Email Agent":          "email",
                "✅ Task Agent":           "task",
                "🎯 Interview Prep":       "interview",
                "📚 Knowledge Search":     "knowledge",
            }
            current_label = next(
                (l for l, k in agent_options.items() if k == st.session_state.active_agent),
                "📧 Email Agent"
            )
            chosen = st.selectbox(
                "Switch agent",
                list(agent_options.keys()),
                index=list(agent_options.keys()).index(current_label),
                label_visibility="collapsed",
            )
            new_key = agent_options[chosen]
            if new_key != st.session_state.active_agent:
                st.session_state.active_agent = new_key
                st.rerun()

        st.markdown("---")

        # Knowledge base file uploader (always visible)
        st.markdown("**📂 Knowledge Base**")
        uploaded = st.file_uploader(
            "Upload files",
            type=["pdf", "docx", "txt", "md", "csv", "py"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded:
            saved = []
            tmp_dir = ROOT / ".kb_uploads"
            tmp_dir.mkdir(exist_ok=True)
            for f in uploaded:
                dest = tmp_dir / f.name
                dest.write_bytes(f.read())
                saved.append(str(dest))
            if set(saved) != set(st.session_state.kb_files):
                st.session_state.kb_files = saved
                # Reset knowledge agent so it rebuilds with new files
                st.session_state.agents.pop("knowledge", None)
                st.success(f"Loaded {len(saved)} file(s)")

        if st.session_state.kb_files:
            st.caption(f"📎 {len(st.session_state.kb_files)} file(s) loaded")
            for fp in st.session_state.kb_files:
                st.caption(f"  • {Path(fp).name}")

        st.markdown("---")
        st.caption(f"Model: `{os.getenv('AGENT_MODEL','openai/gpt-5-nano')}`")
        st.caption(f"User: `{st.session_state.user_id}`")


# ── chat page ─────────────────────────────────────────────────────────────────
def render_chat():
    key = st.session_state.active_agent
    label_map = {
        "main":      "🤖 Main Agent",
        "email":     "📧 Email Agent",
        "task":      "✅ Task Agent",
        "interview": "🎯 Interview Prep Agent",
        "knowledge": "📚 Knowledge Search Agent",
    }
    st.markdown(f'<div class="section-header">{label_map.get(key,"Agent")}</div>',
                unsafe_allow_html=True)

    # Knowledge agent — warn if no files loaded
    if key == "knowledge" and not st.session_state.kb_files:
        st.info("📂 Upload files in the sidebar to activate Knowledge Search.")
        return

    # Chat history container
    history = st.session_state.chat_history.get(key, [])
    chat_container = st.container(height=520, border=False)

    with chat_container:
        if not history:
            hints = {
                "main":      "Try: *'عندي إنترفيو الخميس، جهزلي خطة مذاكرة'* or *'show my tasks'*",
                "email":     "Try: *'show my latest job emails'*",
                "task":      "Try: *'show my tasks for this week'*",
                "interview": "Try: *'scan my emails for interviews'*",
                "knowledge": "Try: *'summarize this document'*",
            }
            st.markdown(f"👋 Hello! {hints.get(key,'')}")

        for msg in history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="bubble-label" style="text-align:right">You</div>'
                    f'<div class="bubble-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="bubble-label">Assistant</div>'
                    f'<div class="bubble-ai">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # Input
    with st.form(key=f"chat_form_{key}", clear_on_submit=True):
        cols = st.columns([8, 1])
        user_input = cols[0].text_input(
            "Message", placeholder="Type a message…", label_visibility="collapsed"
        )
        submitted = cols[1].form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        msg = user_input.strip()
        history.append({"role": "user", "content": msg})
        st.session_state.chat_history[key] = history

        with st.spinner("Thinking…"):
            reply = invoke_agent(key, msg)

        history.append({"role": "assistant", "content": reply})
        st.session_state.chat_history[key] = history
        st.rerun()

    # Approval widget — shown when agent requests HITL confirmation
    render_approval_widget()

    # Clear button
    if history and st.button("🗑 Clear conversation", key=f"clear_{key}"):
        st.session_state.chat_history[key] = []
        st.rerun()


# ── tasks page ────────────────────────────────────────────────────────────────
def render_tasks():
    st.markdown('<div class="section-header">📅 Tasks & Calendar</div>',
                unsafe_allow_html=True)

    col_filter, col_days, _ = st.columns([2, 2, 4])
    status_filter = col_filter.selectbox(
        "Status", ["open", "todo", "in_progress", "done", "all"],
        label_visibility="collapsed"
    )
    days_ahead = col_days.slider("Days ahead", 1, 60, 14, label_visibility="collapsed")

    if st.button("🔄 Refresh"):
        st.rerun()

    tasks = fetch_tasks(status_filter, days_ahead)

    if not tasks:
        st.info("No tasks found. Use the Task Agent to create some!")
        return

    # Group by due_date
    groups: dict[str, list] = {}
    for t in tasks:
        day = (t.get("due_date") or "No due date")[:10]
        groups.setdefault(day, []).append(t)

    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

    for day in sorted(groups.keys()):
        if day == today_str:
            label = f"📌 Today — {day}"
        elif day == tomorrow_str:
            label = f"⏰ Tomorrow — {day}"
        elif day == "No due date":
            label = "📋 No due date"
        else:
            try:
                dt = datetime.strptime(day, "%Y-%m-%d")
                label = dt.strftime("📆 %A, %b %d")
            except ValueError:
                label = day

        with st.expander(label, expanded=(day == today_str)):
            for t in groups[day]:
                priority = t.get("priority", "medium")
                status   = t.get("status", "todo")
                status_icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}.get(status, "⬜")
                st.markdown(
                    f'<div class="task-card {priority}">'
                    f'<div class="task-title">{status_icon} #{t["id"]} {t["title"]}</div>'
                    f'<div class="task-meta">Priority: {priority} &nbsp;|&nbsp; Status: {status}'
                    + (f' &nbsp;|&nbsp; Due: {t["due_date"][:10]}' if t.get("due_date") else "")
                    + (f'<br><em>{t["description"]}</em>' if t.get("description") else "")
                    + "</div></div>",
                    unsafe_allow_html=True,
                )


# ── interview plan page ───────────────────────────────────────────────────────
def render_interview_plan():
    st.markdown('<div class="section-header">🎯 Interview Prep Plan</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    col1.write("Study tasks created by the Interview Prep Agent, grouped by day.")
    if col2.button("🔄 Refresh"):
        st.rerun()

    tasks = fetch_interview_tasks()

    if not tasks:
        st.info(
            "No interview prep tasks yet.\n\n"
            "Go to **Chat → Interview Prep Agent** and say:\n"
            "*'scan my emails for interviews'*"
        )
        return

    # Timeline view
    groups: dict[str, list] = {}
    for t in tasks:
        day = (t.get("due_date") or "Unscheduled")[:10]
        groups.setdefault(day, []).append(t)

    interview_date = max(
        (d for d in groups if d != "Unscheduled"),
        default=None
    )

    if interview_date:
        days_left = (date.fromisoformat(interview_date) - date.today()).days
        if days_left > 0:
            st.success(f"🗓 Interview in **{days_left} day(s)** — {interview_date}")
        elif days_left == 0:
            st.warning("🚨 Interview is **today**! Good luck!")
        else:
            st.info(f"Interview was on {interview_date}")

    st.markdown("---")

    for day in sorted(groups.keys()):
        try:
            dt = datetime.strptime(day, "%Y-%m-%d")
            label = dt.strftime("📅 %A, %B %d")
        except ValueError:
            label = f"📋 {day}"

        with st.expander(label, expanded=True):
            for t in groups[day]:
                priority = t.get("priority", "medium")
                color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(priority, "#94a3b8")
                st.markdown(
                    f'<div class="task-card {priority}">'
                    f'<div class="task-title" style="color:{color}">📖 {t["title"]}</div>'
                    + (f'<div class="task-meta">{t["description"]}</div>' if t.get("description") else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

    # Quick-launch interview agent chat
    st.markdown("---")
    st.markdown("**💬 Talk to Interview Prep Agent**")
    with st.form("interview_quick_chat"):
        q = st.text_input("Ask anything about your prep…", label_visibility="collapsed",
                          placeholder="e.g. 'what should I focus on today?'")
        if st.form_submit_button("Ask"):
            if q.strip():
                with st.spinner("Thinking…"):
                    reply = invoke_agent("interview", q.strip())
                st.markdown(
                    f'<div class="bubble-ai">{reply}</div>',
                    unsafe_allow_html=True,
                )


# ── web search page ───────────────────────────────────────────────────────────
def render_web_search():
    st.markdown('<div class="section-header">🔍 Web Search</div>',
                unsafe_allow_html=True)

    with st.form("search_form"):
        cols = st.columns([7, 1])
        query = cols[0].text_input(
            "Search", placeholder="Search the web…",
            value=st.session_state.search_query,
            label_visibility="collapsed",
        )
        submitted = cols[1].form_submit_button("Search", use_container_width=True)

    if submitted and query.strip():
        st.session_state.search_query = query.strip()
        with st.spinner("Searching…"):
            st.session_state.search_results = do_web_search(query.strip())

    results = st.session_state.search_results
    if results:
        st.markdown(f"**{len(results)} results for:** *{st.session_state.search_query}*")
        st.markdown("---")
        for r in results:
            title   = r.get("title", "No title")
            content = r.get("content", r.get("snippet", ""))
            url     = r.get("url", "")
            st.markdown(
                f'<div class="search-result">'
                f'<div class="search-title">{title}</div>'
                f'<div class="search-snippet">{content[:300]}{"…" if len(content)>300 else ""}</div>'
                f'<div class="search-url"><a href="{url}" target="_blank">{url}</a></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Ask an agent about the results
        st.markdown("---")
        st.markdown("**💬 Ask an agent about these results**")
        with st.form("search_agent_form"):
            agent_choice = st.selectbox(
                "Agent",
                ["task", "email", "interview", "knowledge"],
                format_func=lambda x: {
                    "task": "✅ Task Agent",
                    "email": "📧 Email Agent",
                    "interview": "🎯 Interview Prep",
                    "knowledge": "📚 Knowledge Search",
                }[x],
            )
            follow_up = st.text_input(
                "Follow-up question",
                placeholder="e.g. 'add a task to learn about this topic'",
                label_visibility="collapsed",
            )
            if st.form_submit_button("Send to agent"):
                if follow_up.strip():
                    combined = (
                        f"Web search results for '{st.session_state.search_query}':\n\n"
                        + "\n\n".join(
                            f"- {r.get('title','')}: {r.get('content', r.get('snippet',''))[:200]}"
                            for r in results[:4]
                        )
                        + f"\n\nUser question: {follow_up.strip()}"
                    )
                    with st.spinner("Thinking…"):
                        reply = invoke_agent(agent_choice, combined)
                    st.markdown(
                        f'<div class="bubble-ai">{reply}</div>',
                        unsafe_allow_html=True,
                    )


# ── knowledge page ────────────────────────────────────────────────────────────
def render_knowledge():
    st.markdown('<div class="section-header">📚 Knowledge Base</div>',
                unsafe_allow_html=True)

    if not st.session_state.kb_files:
        st.info("📂 Upload files using the sidebar uploader to get started.")
        return

    st.success(f"✅ {len(st.session_state.kb_files)} file(s) loaded and indexed.")
    for fp in st.session_state.kb_files:
        st.markdown(f"- `{Path(fp).name}`")

    st.markdown("---")
    st.markdown("**💬 Chat with your documents**")

    history = st.session_state.chat_history.get("knowledge", [])
    chat_container = st.container(height=400, border=False)
    with chat_container:
        if not history:
            st.markdown("👋 Ask anything about your uploaded documents!")
        for msg in history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="bubble-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="bubble-ai">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    with st.form("kb_chat_form", clear_on_submit=True):
        cols = st.columns([8, 1])
        user_input = cols[0].text_input(
            "Ask", placeholder="Ask about your documents…",
            label_visibility="collapsed"
        )
        submitted = cols[1].form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        msg = user_input.strip()
        history.append({"role": "user", "content": msg})
        st.session_state.chat_history["knowledge"] = history
        with st.spinner("Searching documents…"):
            reply = invoke_agent("knowledge", msg)
        history.append({"role": "assistant", "content": reply})
        st.session_state.chat_history["knowledge"] = history
        st.rerun()


# ── router ────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    page = st.session_state.page
    if page == "chat":
        render_chat()
    elif page == "tasks":
        render_tasks()
    elif page == "interview_plan":
        render_interview_plan()
    elif page == "web_search":
        render_web_search()
    elif page == "knowledge":
        render_knowledge()


main()
