# Productive Agent

An AI-powered personal productivity assistant that coordinates specialist agents for email management, task scheduling, interview preparation, and document Q&A.

## Architecture

```
User → Main Agent (orchestrator)
         ├── Email Agent     — Gmail search, summarize, draft & send replies
         ├── Task Agent      — SQLite tasks + Google Calendar scheduling
         ├── Interview Agent — CV + email + study plan generation
         ├── Knowledge Agent — RAG over uploaded documents (PDF, DOCX, TXT…)
         └── Web Search      — Tavily search
```

All agents share a **long-term memory** (SQLite `data/memory.db`) for user facts and conversation summaries, and **short-term memory** (LangGraph `InMemorySaver`) for per-session conversation history.

## Project Structure

```
productive_Agent/
├── app.py                  # Streamlit UI
├── main.py                 # CLI entry point
├── pyproject.toml          # Package metadata & dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── src/productive_agent/
│   ├── core/
│   │   ├── config.py       # LLM factory (make_model)
│   │   └── memory.py       # Short- and long-term memory
│   ├── agents/
│   │   ├── orchestrator.py # Main orchestrator agent
│   │   ├── email_agent.py  # Email agent
│   │   ├── task_agent.py   # Task + calendar agent
│   │   ├── interview_agent.py
│   │   └── knowledge_agent.py
│   └── tools/
│       ├── gmail.py        # Gmail @tool functions
│       ├── calendar.py     # Google Calendar @tool functions
│       ├── web_search.py   # Tavily web search
│       └── cv_reader.py    # PDF CV reader
├── data/                   # SQLite databases (gitignored)
└── credentials/            # OAuth files (gitignored)
```

## Setup

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required keys:
- `OPENROUTER_API_KEY` — get from [openrouter.ai](https://openrouter.ai)
- `TAVILY_API_KEY` — get from [tavily.com](https://tavily.com) (for web search)

### 3. Google API setup (Gmail + Calendar)

1. Create a project at [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Gmail API** and **Google Calendar API**
3. Create OAuth 2.0 credentials (Desktop App)
4. Download `credentials.json` and place it in `credentials/`
5. On first run, a browser window will open for authorization

### 4. Add your CV

Place your CV PDF in `agent/` or set `INTERVIEW_CV_PATH` in `.env`.

## Running

### Streamlit UI (recommended)

```bash
streamlit run app.py
```

### CLI

```bash
python main.py                  # Main orchestrator
python main.py --agent email    # Email agent directly
python main.py --agent task     # Task agent directly
python main.py --agent interview
python main.py --agent knowledge
```

## Features

- **Long & short-term memory** — facts and summaries persist across sessions
- **Human-in-the-loop** — email sending and task deletion require explicit approval
- **Multi-language** — replies in the language the user writes in (Arabic/English)
- **Calendar sync** — tasks with due dates can be synced to Google Calendar
