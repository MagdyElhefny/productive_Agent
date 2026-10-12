import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# .env lives at the project root (two levels above this file: src/productive_agent/core/)
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env", override=True)


def make_model(model_name: str = None, temperature: float = 0) -> ChatOpenAI:
    """Create a ChatOpenAI model routed through OpenRouter.

    model_name: OpenRouter model id, e.g. "openai/gpt-5-nano"
                Defaults to AGENT_MODEL env var.
    """
    name = model_name or os.getenv("AGENT_MODEL", "openai/gpt-5-nano")

    return ChatOpenAI(
        model=name,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )


# Default model instance — imported by other agents
model = make_model()
