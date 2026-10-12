"""
Web search tool using Tavily.
Extracted from the original web_search.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

from langchain.tools import tool
from tavily import TavilyClient

from ..core.config import make_model

tavilyClient = TavilyClient()


@tool
def web_search(query: str) -> str:
    """Search the web for external information."""
    return tavilyClient.search(query)


# LLM with the web_search tool bound — used by other agents
web_search_agent = make_model().bind_tools([web_search])
