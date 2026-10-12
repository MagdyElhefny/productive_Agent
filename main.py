"""
Productive Agent — Main Entry Point
=====================================
Defaults to the Main Agent (central orchestrator).
You can still access individual agents via the --agent flag.

Run:
    python main.py              # Main orchestrator (recommended)
    python main.py --agent email
    python main.py --agent task
    python main.py --agent interview
    python main.py --agent knowledge
"""

import os
import sys
from pathlib import Path

# Add src/ to the import path so productive_agent package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
# Keep agent/ on path for backward compat (legacy code may import from there)
sys.path.insert(1, str(Path(__file__).resolve().parent / "agent"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


def main():
    # Check for --agent flag
    agent_flag = None
    if "--agent" in sys.argv:
        idx = sys.argv.index("--agent")
        if idx + 1 < len(sys.argv):
            agent_flag = sys.argv[idx + 1].lower()

    if agent_flag == "email":
        from productive_agent.agents.email_agent import main as run
        run()
    elif agent_flag == "task":
        from productive_agent.agents.task_agent import main as run
        run()
    elif agent_flag == "interview":
        from productive_agent.agents.interview_agent import main as run
        run()
    elif agent_flag == "knowledge":
        from productive_agent.agents.knowledge_agent import main as run
        run()
    else:
        # Default: main orchestrator
        from productive_agent.agents.orchestrator import main as run
        run()


if __name__ == "__main__":
    main()
