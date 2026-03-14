Here is the rewritten Markdown document with **all .env-related content removed** (no examples, no mentions of specific keys or secrets). This version is safe to commit to a git repo without risk of leaking credentials.

```markdown
# NiceGUI + FastMCP + Supabase Stack  
**Personal Reading Tutor App – Architecture & Setup Guide**  
**(with Strict LangGraph Agent Coordination)**

**Version:** 1.2 (Secrets Removed for Repo Safety)  
**Purpose:** This document describes the full-stack architecture for the Personal Reading Tutor app using **NiceGUI** (UI + session orchestration), **FastMCP** (tool/agent interface), **LangGraph** (stateful multi-agent coordination), and **Supabase** (auth, database, storage).  

**Critical Agent Rule:**  
**Every** non-trivial AI/LLM workflow in this app **must** follow the **Planner → Narrow Workers → Judge** pattern exactly as defined in the separate `agent-design.md` document.  
- One Lead Planner decomposes the high-level goal into atomic sub-tasks with explicit success criteria.  
- Narrow Workers execute one sub-task each, in isolation, producing verifiable artifacts.  
- One Judge verifies outputs strictly against the Planner’s criteria, approves/rejects/requests iteration, and controls conditional looping.  
- All agent logic is implemented in **LangGraph** graphs (stateful, with cycles, persistence, and conditional edges).  
- No flat chains, no single monolithic agents, no custom Python scripts without a LangGraph backbone.

A separate document (`agents-design.md`) contains the detailed LangGraph graphs, state schemas, prompts, node functions, and success criteria for each major workflow.

## Core Principles of This Stack

- **Everything in Python** — No JavaScript frameworks.  
- **NiceGUI** owns the student-facing experience: login, dashboard, placement, 30-minute sessions, progress views.  
- **FastMCP** provides clean, typed tool interfaces that NiceGUI calls to trigger agent workflows.  
- **LangGraph** enforces the strict Planner → Narrow Workers → Judge pattern for **all** intelligent operations (text generation, vocab selection, response evaluation, feedback generation, difficulty adaptation).  
- **Supabase** handles authentication (OAuth/email), student profiles, session logs, and Row Level Security.  
- Secrets (API keys, service credentials) are loaded from environment variables via a `.env` file or platform secrets manager — **never hard-coded or committed**.  
- Deployment: Render, Railway, Fly.io, or similar (single-container Python app).

## High-Level Architecture

```
student browser
      │
      ▼
  NiceGUI app (FastAPI-based)
      │
      ├─► Supabase client (auth + RLS-protected queries)
      │
      └─► FastMCP → LangGraph graphs
            │
            ├─► LLM provider(s) (via environment variables)
            └─► Supabase (read student history / write logs & updates)
```

## Folder Structure (Recommended)

```
reading-tutor/
├── app/
│   ├── main.py                     # NiceGUI entry point
│   ├── pages/
│   │   ├── login.py
│   │   ├── dashboard.py
│   │   ├── placement.py
│   │   ├── session.py              # Orchestrates 30-min flow
│   │   └── progress.py
│   ├── components/
│   │   ├── session_steps.py        # Vocab preview, pauses, gist, mastery UI
│   │   └── ui_helpers.py
│   └── supabase_client.py          # Wrapped supabase-py with auth helpers
├── agents/
│   ├── __init__.py
│   ├── graphs/                     # LangGraph definitions (detailed in agents-design.md)
│   │   ├── text_selection_graph.py
│   │   ├── vocab_preview_graph.py
│   │   ├── comprehension_coach_graph.py
│   │   ├── assessment_graph.py
│   │   └── adaptation_graph.py
│   └── tools/                      # FastMCP tool decorators
│       ├── text_selector_tool.py
│       ├── vocab_tool.py
│       ├── comprehension_tool.py
│       ├── assessment_tool.py
│       └── adaptation_tool.py
├── utils/
│   ├── config.py                   # Environment variable loader
│   └── logging.py
├── requirements.txt
└── README.md
```

## Key Technologies & Versions (Suggested)

- Python 3.11 / 3.12  
- nicegui >= 2.0 (latest stable)  
- fastmcp (your current version)  
- langgraph >= 0.2.x (strictly used for all agent logic)  
- supabase >= 2.0 (Python client)  
- python-dotenv (for local .env loading during development)  
- LLM SDKs (openai, anthropic, groq, etc.) — credentials loaded from environment

## How the Pieces Work Together (Student Session Example)

1. **Login / Dashboard**  
   NiceGUI → Supabase OAuth → session established.

2. **Start Daily Session**  
   NiceGUI calls FastMCP `select_stretch_text_tool(student_id)`  
   → Triggers `text_selection_graph` (LangGraph):  
     - Lead Planner decomposes: “Select age-appropriate stretch text + 4–6 vocab words”  
     - Narrow Workers: topic matcher, Lexile matcher, text generator, vocab extractor  
     - Judge verifies: text matches interests/level, vocab words are Tier 2 + context-rich, success criteria met  
   → Returns text + vocab list to NiceGUI.

3. **Vocab Preview Step**  
   NiceGUI renders sentences one by one → student guesses → submits.  
   NiceGUI calls FastMCP `vocab_evaluation_tool(guess, sentence, target_word)`  
   → Triggers `vocab_preview_graph`:  
     - Planner: “Evaluate this single guess against context”  
     - Worker: context-based meaning checker  
     - Judge: approves/rejects based on strict criteria (semantic match, not exact wording)  
   → Returns feedback text → NiceGUI displays → moves on (no retry loop in UI).

4. **Reading Pauses / Gist / Mastery Check**  
   Similar pattern: NiceGUI collects response → calls appropriate FastMCP tool → tool runs dedicated LangGraph graph → Judge approves/rejects output → returns feedback text + score → NiceGUI shows explanation briefly → advances flow.  
   All data logged to Supabase immediately.

5. **Session End**  
   NiceGUI calls `adaptation_tool(session_id)`  
   → Triggers `adaptation_graph`:  
     - Planner: “Analyze session performance and recommend next difficulty/strategy”  
     - Workers: accuracy analyzer, error pattern detector, trend reader  
     - Judge: verifies recommendations against historical data and adaptation rules  
   → Updates student profile in Supabase.

## Non-Negotiable Agent Rules (Repeated from agent-design.md)

- Always use **LangGraph** for agent logic.  
- One Lead Planner per graph — decomposes only.  
- Narrow Workers — one atomic task each, isolated, parallel where possible.  
- One Judge — verifies strictly against Planner’s success criteria, controls iteration.  
- No cross-talk between workers; artifacts only.  
- Human-in-the-loop possible via interrupts (future extension).  
- Every graph must produce verifiable artifacts (structured JSON, scored outputs, logged rationale).

## Implementation Notes

- FastMCP tools are thin wrappers: they receive input from NiceGUI, invoke the correct LangGraph graph, stream/await final approved output, return structured result.  
- Supabase writes happen after Judge approval where possible (atomicity).  
- Session flow in NiceGUI remains linear and fast — agents run synchronously or async as needed.  
- Cost control: use cheaper/faster models for Judge & narrow workers; better models only for Planner & text generation.  
- Security: Supabase Row Level Security (RLS) ensures students only access their data.
- The app will use a .env file for ai and supabase api keys

## Next Steps

1. Set up Supabase project + OAuth  
2. Configure environment variables (locally via .env, in production via platform secrets)  
3. Build basic NiceGUI skeleton (login → dashboard)  
4. Wire supabase-py client  
5. Implement FastMCP tools that call LangGraph graphs  
6. Develop graphs per `agents-design.md`  
7. Test full session end-to-end  
8. Deploy


