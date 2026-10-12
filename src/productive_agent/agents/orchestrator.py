"""
Main Productivity Agent — Central Orchestrator
===============================================
A single entry point that understands the user's intent and delegates
to the appropriate specialist agents and tools.

Architecture:
  User → Main Agent → [email_agent | task_agent | interview_agent |
                        knowledge_agent | web_search]
"""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

from langchain.agents import create_agent
from langchain.tools import tool

from ..core.config import make_model
from ..core.memory import MemoryStore, get_short_term_checkpointer, make_memory_tools
from ..agents.task_agent import init_db, Context as TaskContext

# ---------------------------------------------------------------------------
# Sub-agent registry  (lazy — built on first call, cached after)
# ---------------------------------------------------------------------------
_registry: dict = {}


def _get(key: str, user_id: str, kb_files: list[str] | None = None) -> dict:
    """Return or lazily build a sub-agent entry {agent, config, context}."""
    cache_key = f"{key}:{user_id}"
    if cache_key in _registry:
        return _registry[cache_key]

    if key == "email":
        from ..agents.email_agent import build_agent
        agent = build_agent(user_id=user_id)
        entry = {
            "agent":   agent,
            "config":  {"configurable": {"thread_id": f"email-{user_id}"}},
            "context": None,
        }

    elif key == "task":
        from ..agents.task_agent import build_agent
        init_db()
        agent = build_agent(user_id=user_id)
        entry = {
            "agent":   agent,
            "config":  {"configurable": {"thread_id": f"task-{user_id}"}},
            "context": TaskContext(user_id=user_id),
        }

    elif key == "interview":
        from ..agents.interview_agent import build_agent, Context as IContext
        init_db()
        agent = build_agent(user_id=user_id)
        entry = {
            "agent":   agent,
            "config":  {"configurable": {"thread_id": f"interview-{user_id}"}},
            "context": IContext(user_id=user_id),
        }

    elif key == "knowledge":
        if not kb_files:
            return {}
        from ..agents.knowledge_agent import build_agent
        agent = build_agent(kb_files, user_id=user_id)
        entry = {
            "agent":   agent,
            "config":  {"configurable": {"thread_id": f"knowledge-{user_id}"}},
            "context": None,
        }

    else:
        return {}

    _registry[cache_key] = entry
    return entry


def _invoke(key: str, message: str, user_id: str,
            kb_files: list[str] | None = None) -> str:
    """Send a message to a sub-agent and return its text response."""
    entry = _get(key, user_id, kb_files)
    if not entry:
        return f"[{key} agent] Not available (no files loaded for knowledge agent)."

    agent   = entry["agent"]
    config  = entry["config"]
    context = entry.get("context")
    payload = {"messages": [{"role": "user", "content": message}]}

    try:
        result = (
            agent.invoke(payload, config=config, context=context)
            if context else
            agent.invoke(payload, config=config)
        )
        content = result["messages"][-1].content
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        return content
    except Exception as e:
        return f"[{key} agent error] {e}"


# ---------------------------------------------------------------------------
# Orchestrator tools
# ---------------------------------------------------------------------------

def make_orchestrator_tools(user_id: str, kb_files: list[str] | None = None):
    """Build and return all orchestrator tool functions for this user."""

    @tool
    def email_agent(task: str) -> str:
        """Delegate an email-related task to the Email Agent.

        Use for:
        - Searching Gmail (job emails, interview invitations, any emails)
        - Reading or summarizing a specific email
        - Drafting or sending a reply
        - Anything involving the inbox

        Pass the full task description including any context needed.
        """
        return _invoke("email", task, user_id)

    @tool
    def task_agent(task: str) -> str:
        """Delegate a task/calendar request to the Task & Schedule Agent.

        Use for:
        - Creating, updating, listing, or deleting tasks
        - Checking the calendar for free slots
        - Scheduling something on a specific date
        - Asking what is planned for a day or week

        Pass the full task description including dates or deadlines.
        """
        return _invoke("task", task, user_id)

    @tool
    def interview_prep_agent(task: str) -> str:
        """Delegate interview preparation work to the Interview Prep Agent.

        Use for:
        - Scanning Gmail for interview emails
        - Building a study plan based on a job description and the user's CV
        - Generating interview questions and topics
        - Distributing prep tasks across available days

        Pass the full task description including the interview date if known.
        """
        return _invoke("interview", task, user_id)

    @tool
    def knowledge_agent(task: str) -> str:
        """Delegate document Q&A to the Knowledge Search Agent.

        Use for:
        - Answering questions about an uploaded document
        - Summarizing a PDF, DOCX, or text file
        - Searching for specific information in loaded files

        Only available when files have been loaded.
        Pass the specific question or section to look up.
        """
        return _invoke("knowledge", task, user_id, kb_files)

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information using Tavily.

        Use for:
        - Looking up recent news, documentation, or facts
        - Researching a company before an interview
        - Finding answers not available in the user's documents or emails

        Pass a clear, focused search query.
        """
        try:
            from tavily import TavilyClient
            results = TavilyClient().search(query, max_results=5)
            items = results.get("results", [])
            if not items:
                return "No results found."
            return "\n\n".join(
                f"**{r.get('title','')}**\n{r.get('content','')[:300]}\n{r.get('url','')}"
                for r in items
            )
        except Exception as e:
            return f"[web search error] {e}"

    return [email_agent, task_agent, interview_prep_agent, knowledge_agent, web_search]


# ---------------------------------------------------------------------------
# Main agent builder
# ---------------------------------------------------------------------------

def build_main_agent(user_id: str = "local-user",
                     kb_files: list[str] | None = None):
    """Build the central orchestrator agent."""
    llm = make_model()
    mem = MemoryStore(user_id)
    memory_context = mem.build_context_block()

    today = date.today().isoformat()

    system_prompt = f"""You are a smart personal productivity assistant.
Today is {today}. Reply in the language the user writes in.
{memory_context}

You coordinate four specialist agents and a web search tool to fulfill complex requests.
Think step-by-step, break multi-part requests into sub-tasks, and call the right agent
for each part. Never attempt to do domain work yourself — always delegate.

━━━ YOUR AGENTS ━━━

📧 email_agent
  Search Gmail, read emails, summarize, draft replies, send drafts.
  → Use when: user mentions emails, inbox, job offers, recruiter messages.

✅ task_agent
  Create / list / update / delete tasks, check calendar, find free slots.
  → Use when: user wants to schedule, plan, track, or review tasks/calendar.

🎯 interview_prep_agent
  Scan Gmail for interview emails + read CV + build study plan + save tasks.
  → Use when: user mentions interview, job prep, study plan, CV analysis.
  → This agent coordinates email + task automatically — prefer it for interview requests.

📚 knowledge_agent
  Answer questions about uploaded documents (PDF, DOCX, TXT).
  → Use when: user asks about a file they uploaded.

🔍 web_search
  Search the internet for current information.
  → Use when: user asks about news, company info, docs, or anything external.

━━━ HOW TO HANDLE MULTI-STEP REQUESTS ━━━
Example: "I have an interview Thursday — build a study plan and email me the details."
  Step 1 → interview_prep_agent: "Scan emails for Thursday interview, read CV, build study plan, save tasks"
  Step 2 → email_agent: "Draft an email to me summarizing the study plan just created"

Always:
- Use remember_fact to save important user information for future sessions.
- Use recall_facts to check what you already know before asking the user.
- If a step's output is needed by the next step, include it in the next tool call.
- Report clearly what each agent did and what the final result is.
- If an agent returns an APPROVAL_REQUIRED sentinel, relay it to the user exactly."""

    tools = [
        *make_orchestrator_tools(user_id, kb_files),
        *make_memory_tools(user_id),
    ]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=get_short_term_checkpointer(),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    user_id = os.getenv("TASK_AGENT_USER", "local-user")
    init_db()
    mem = MemoryStore(user_id)
    agent = build_main_agent(user_id=user_id)
    config = {"configurable": {"thread_id": f"main-{user_id}"}}

    print("╔══════════════════════════════════════╗")
    print("║   Productive Agent  —  Main Agent    ║")
    print("╚══════════════════════════════════════╝")
    print("Tell me what you need. I'll coordinate everything.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "خروج"}:
            print("Goodbye!")
            break

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
        content = result["messages"][-1].content
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))

        if isinstance(content, str) and content.startswith("APPROVAL_REQUIRED|"):
            parts = content.split("|", 3)
            action  = parts[1] if len(parts) > 1 else ""
            item_id = parts[2] if len(parts) > 2 else ""
            preview = parts[3] if len(parts) > 3 else ""
            print(f"\n{'='*60}\nAPPROVAL REQUIRED\n{preview}\n{'='*60}")
            answer = input("Confirm? (yes / cancel): ").strip().lower()
            if answer in {"yes", "y", "نعم", "ايوه"}:
                if action == "send_email":
                    from ..tools.gmail import _send_draft_execute
                    print(_send_draft_execute(item_id))
                elif action == "delete_task":
                    from ..agents.task_agent import _delete_task_execute
                    print(_delete_task_execute(user_id, int(item_id)))
            else:
                print("Action cancelled.")
            print()
        else:
            try:
                short = (content[:120] + "…") if len(content) > 120 else content
                mem.save_summary("main", short)
            except Exception:
                pass
            print(f"\nAssistant: {content}\n")


if __name__ == "__main__":
    main()
