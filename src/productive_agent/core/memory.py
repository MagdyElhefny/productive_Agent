"""
Shared Memory Module
====================
Provides both short-term and long-term memory for all agents.

Short-term memory:
  - Per-session conversation history via LangGraph's InMemorySaver.
  - Scoped by thread_id — lives only while the process is running.

Long-term memory (SQLite-backed, persists across restarts):
  - User facts: key-value facts the user states ("my timezone is Cairo",
    "I prefer Python over Java").  Agents can read and write these.
  - Conversation summaries: after each turn the agent can save a one-line
    summary of what happened.  Used to prime future sessions with context.

All long-term data is scoped by user_id so multi-user setups work correctly.

Usage:
    from productive_agent.core.memory import MemoryStore, get_short_term_checkpointer

    mem = MemoryStore(user_id="local-user")
    context_block = mem.build_context_block()
    mem.save_fact("preferred_language", "Python")
    mem.save_summary("email", "User asked to summarize interview email from Google")
    checkpointer = get_short_term_checkpointer()
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

# .env lives at the project root (three levels up: src/productive_agent/core/ -> root)
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

# ---------------------------------------------------------------------------
# Storage path — points to data/ at project root
# ---------------------------------------------------------------------------
MEMORY_DB_PATH = os.getenv(
    "MEMORY_DB_PATH", str(_ROOT / "data" / "memory.db")
)

# ---------------------------------------------------------------------------
# Short-term: one shared InMemorySaver per process
# ---------------------------------------------------------------------------
_short_term_checkpointer = None


def get_short_term_checkpointer() -> InMemorySaver:
    """Return the shared in-process checkpointer for all agents."""
    global _short_term_checkpointer
    if _short_term_checkpointer is None:
        _short_term_checkpointer = InMemorySaver()
    return _short_term_checkpointer


# ---------------------------------------------------------------------------
# Long-term DB helpers
# ---------------------------------------------------------------------------
@contextmanager
def _db():
    conn = sqlite3.connect(MEMORY_DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_memory_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                key        TEXT    NOT NULL,
                value      TEXT    NOT NULL,
                source     TEXT    NOT NULL DEFAULT 'agent',
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL,
                UNIQUE(user_id, key)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts(user_id)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                agent      TEXT    NOT NULL,
                summary    TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_summaries_user "
            "ON conversation_summaries(user_id, agent)"
        )


# ---------------------------------------------------------------------------
# MemoryStore — one instance per user
# ---------------------------------------------------------------------------
class MemoryStore:
    """Read/write long-term memory for a specific user."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        init_memory_db()

    # ── facts ────────────────────────────────────────────────────────────
    def save_fact(self, key: str, value: str, source: str = "agent"):
        """Upsert a user fact. Key is case-insensitive."""
        key = key.strip().lower()
        now = datetime.now().isoformat(timespec="seconds")
        with _db() as conn:
            conn.execute("""
                INSERT INTO user_facts (user_id, key, value, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, key)
                DO UPDATE SET value=excluded.value,
                              source=excluded.source,
                              updated_at=excluded.updated_at
            """, (self.user_id, key, value.strip(), source, now, now))

    def get_fact(self, key: str) -> str | None:
        key = key.strip().lower()
        with _db() as conn:
            row = conn.execute(
                "SELECT value FROM user_facts WHERE user_id=? AND key=?",
                (self.user_id, key)
            ).fetchone()
        return row["value"] if row else None

    def get_all_facts(self) -> dict[str, str]:
        with _db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM user_facts WHERE user_id=? ORDER BY key",
                (self.user_id,)
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_fact(self, key: str):
        key = key.strip().lower()
        with _db() as conn:
            conn.execute(
                "DELETE FROM user_facts WHERE user_id=? AND key=?",
                (self.user_id, key)
            )

    # ── summaries ────────────────────────────────────────────────────────
    def save_summary(self, agent: str, summary: str):
        """Append a one-line summary of a conversation turn."""
        now = datetime.now().isoformat(timespec="seconds")
        with _db() as conn:
            conn.execute(
                "INSERT INTO conversation_summaries "
                "(user_id, agent, summary, created_at) VALUES (?, ?, ?, ?)",
                (self.user_id, agent, summary.strip(), now)
            )

    def get_recent_summaries(self, agent: str | None = None, limit: int = 10) -> list[dict]:
        """Return the most recent summaries, optionally filtered by agent."""
        with _db() as conn:
            if agent:
                rows = conn.execute(
                    "SELECT agent, summary, created_at FROM conversation_summaries "
                    "WHERE user_id=? AND agent=? ORDER BY created_at DESC LIMIT ?",
                    (self.user_id, agent, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT agent, summary, created_at FROM conversation_summaries "
                    "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                    (self.user_id, limit)
                ).fetchall()
        return [dict(r) for r in rows]

    # ── context block ────────────────────────────────────────────────────
    def build_context_block(self, agent: str | None = None) -> str:
        """Build a formatted string to inject into system prompts."""
        parts = []

        facts = self.get_all_facts()
        if facts:
            facts_lines = "\n".join(f"  - {k}: {v}" for k, v in facts.items())
            parts.append(f"[Known facts about this user]\n{facts_lines}")

        summaries = self.get_recent_summaries(agent=None, limit=5)
        if summaries:
            summary_lines = "\n".join(
                f"  [{s['agent']} @ {s['created_at'][:16]}] {s['summary']}"
                for s in reversed(summaries)
            )
            parts.append(f"[Recent conversation history]\n{summary_lines}")

        if not parts:
            return ""

        return (
            "\n\n--- Long-term memory ---\n"
            + "\n\n".join(parts)
            + "\n--- End memory ---"
        )


# ---------------------------------------------------------------------------
# LangChain tools: let agents write to long-term memory
# ---------------------------------------------------------------------------
from langchain.tools import tool


def make_memory_tools(user_id: str):
    """Return a list of LangChain tools for reading/writing long-term memory."""
    store = MemoryStore(user_id)

    @tool
    def remember_fact(key: str, value: str) -> str:
        """Save an important fact about the user for future sessions.
        Use this when the user states a preference, personal detail, or
        any information that should be remembered across conversations.
        Examples: key='timezone', value='Africa/Cairo'
                  key='preferred_language', value='Python'
                  key='job_title', value='Junior AI Engineer'
        """
        store.save_fact(key, value, source="agent")
        return f"Remembered: {key} = {value}"

    @tool
    def recall_facts() -> str:
        """Retrieve all facts previously remembered about this user."""
        facts = store.get_all_facts()
        if not facts:
            return "No facts remembered yet."
        return "\n".join(f"{k}: {v}" for k, v in facts.items())

    @tool
    def forget_fact(key: str) -> str:
        """Delete a previously remembered fact by key."""
        store.delete_fact(key)
        return f"Forgotten: {key}"

    return [remember_fact, recall_facts, forget_fact]
