"""
Knowledge Search Agent
======================
Load one or more external files and chat with their content.

Supported file types: PDF, DOCX, TXT, MD, CSV, code files.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core.config import make_model
from ..core.memory import MemoryStore, get_short_term_checkpointer, make_memory_tools

# ---------------------------------------------------------------------------
# Embeddings (loaded once — uses CPU, no API key needed)
# ---------------------------------------------------------------------------
_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        print("Loading embedding model (first time may take a minute)...")
        _embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------
def load_file(path: str):
    """Load a file and return a list of LangChain Documents."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    ext = p.suffix.lower()

    if ext == ".pdf":
        loader = PyMuPDFLoader(str(p))
    elif ext == ".docx":
        loader = Docx2txtLoader(str(p))
    elif ext == ".csv":
        loader = CSVLoader(str(p))
    elif ext in (".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".rs"):
        loader = TextLoader(str(p), encoding="utf-8")
    else:
        loader = TextLoader(str(p), encoding="utf-8")

    docs = loader.load()
    for doc in docs:
        doc.metadata["source_file"] = p.name
    return docs


def build_vector_store(file_paths: list[str]) -> InMemoryVectorStore:
    """Load files, split, embed, and return a vector store."""
    all_docs = []
    for fp in file_paths:
        print(f"  Loading: {fp}")
        docs = load_file(fp)
        all_docs.extend(docs)

    if not all_docs:
        raise ValueError("No content loaded from the provided files.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    splits = splitter.split_documents(all_docs)
    print(f"  Split into {len(splits)} chunks. Building index...")

    store = InMemoryVectorStore(get_embeddings())
    store.add_documents(splits)
    print(f"  Index ready.\n")
    return store


# ---------------------------------------------------------------------------
# Agent builder
# ---------------------------------------------------------------------------
def build_agent(file_paths: list[str], user_id: str = "local-user"):
    """Build a RAG agent over the given files."""
    vector_store = build_vector_store(file_paths)
    file_names = ", ".join(Path(fp).name for fp in file_paths)
    mem = MemoryStore(user_id)
    memory_context = mem.build_context_block(agent="knowledge")

    @tool
    def search_documents(query: str) -> str:
        """Search the loaded documents for information relevant to the query.
        Use this for every question about the file content.
        Returns the most relevant passages with their source.
        """
        results = vector_store.similarity_search(query, k=4)
        if not results:
            return "No relevant content found."
        parts = []
        for i, doc in enumerate(results, 1):
            src = doc.metadata.get("source_file", "unknown")
            page = doc.metadata.get("page", "")
            loc = f"{src}" + (f" p.{page}" if page != "" else "")
            parts.append(f"[{i}] ({loc})\n{doc.page_content.strip()}")
        return "\n\n---\n\n".join(parts)

    @tool
    def list_loaded_files() -> str:
        """Return the names of the files currently loaded."""
        return f"Loaded files: {file_names}"

    model = make_model()

    system_prompt = f"""You are a helpful assistant that answers questions about the user's documents.
Loaded files: {file_names}
{memory_context}

Rules:
- ALWAYS call search_documents before answering any question about the content.
- Quote or reference the source passage when answering.
- If the answer is not in the documents, say so clearly — don't make things up.
- You can summarize, compare, explain, or break down content from the documents.
- If the user asks to "summarize the whole document", call search_documents multiple times
  with different broad queries to cover all sections, then synthesize a full summary.
- Use remember_fact to save any important user preferences mentioned in conversation.
- Reply in the same language the user writes in."""

    return create_agent(
        model=model,
        tools=[search_documents, list_loaded_files, *make_memory_tools(user_id)],
        system_prompt=system_prompt,
        checkpointer=get_short_term_checkpointer(),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) > 1:
        file_paths = sys.argv[1:]
    else:
        print("Knowledge Search Agent")
        print("Enter one or more file paths (comma-separated or one per line).")
        raw = input("File(s): ").strip()
        if not raw:
            print("No file provided. Exiting.")
            return
        file_paths = [p.strip().strip('"').strip("'") for p in raw.replace(",", " ").split() if p.strip()]

    print(f"\nBuilding knowledge base from {len(file_paths)} file(s)...")
    user_id = os.getenv("TASK_AGENT_USER", "local-user")
    try:
        agent = build_agent(file_paths, user_id=user_id)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return

    config = {"configurable": {"thread_id": "knowledge-session-1"}}

    print("Ready! Ask anything about your document(s). Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit", "خروج"}:
            break
        if not user_input:
            continue

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        content = result["messages"][-1].content
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        print(f"\nAssistant: {content}\n")


if __name__ == "__main__":
    main()
