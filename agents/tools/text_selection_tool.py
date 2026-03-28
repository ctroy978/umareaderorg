"""
Tool wrapper for the text_selection LangGraph agent.

Called directly as a Python function from session.py (blocking, run in executor).
The FastMCP decorator is present for future remote deployment via mcp_server.py.
"""
import json
import time

from app.supabase_client import get_profile, log_agent_run, get_topic_from_bank
from app.data.session_content import (
    PASSAGE_TITLE as _FALLBACK_TITLE,
    PASSAGE_SECTIONS as _FALLBACK_SECTIONS,
    VOCAB_WORDS as _FALLBACK_VOCAB_WORDS,
)

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from agents.graphs.text_selection.graph import build_text_selection_graph
        _graph = build_text_selection_graph()
    return _graph


def _dummy_vocab_format(vocab_words: list[dict]) -> list[dict]:
    """Return fallback vocab words (already in MCQ format)."""
    return list(vocab_words)


def select_stretch_text_tool(
    student_id: str,
    session_id: str | None = None,
    access_token: str | None = None,
    topic_override: str | None = None,
    strategy_hint: str | None = None,
    strategy_chunk_index: int | None = None,
) -> dict:
    """
    Run the text_selection agent to generate a personalized reading passage.

    Returns:
        {title, sections, vocab, target_level, rationale}

    Falls back to dummy content on any exception.
    """
    start = time.monotonic()
    input_json = {"student_id": student_id, "session_id": session_id, "topic_override": topic_override, "strategy_hint": strategy_hint}

    try:
        profile = get_profile(student_id, access_token=access_token)
        reading_level = (profile or {}).get("reading_level", "800L")
        interests = (profile or {}).get("interests", [])
        if isinstance(interests, str):
            interests = [interests]
        if not interests:
            interests = ["science", "nature"]

        bank_topic_id = None
        if topic_override:
            bank_row = get_topic_from_bank(topic_override, student_id)
            if bank_row:
                bank_topic_id = bank_row["id"]
                facts_str = "\n".join(f"- {f}" for f in (bank_row.get("key_facts") or []))
                topic_override = (
                    f"{bank_row['topic']}\n\n"
                    f"Open section 1 with this hook (or very close to it): {bank_row['hook']}\n\n"
                    f"Key facts to weave into the passage (use specific numbers and names):\n{facts_str}"
                )

        initial_state = {
            "student_id": student_id,
            "reading_level": reading_level,
            "interests": interests,
            "topic": topic_override,
            "generated_text": None,
            "title": None,
            "vocab": None,
            "judge_feedback": {},
            "retry_counts": {},
            "current_step": None,
            "next_action": None,
            "plan_summary": None,
            "iteration": 0,
            "strategy_hint": strategy_hint,
            "strategy_chunk_index": strategy_chunk_index if strategy_chunk_index is not None else 1,
        }

        graph = _get_graph()
        result = graph.invoke(initial_state)

        # Parse generated_text JSON string → list of section dicts
        raw_sections = result.get("generated_text")
        if raw_sections:
            sections = json.loads(raw_sections)
        else:
            sections = _FALLBACK_SECTIONS

        title = result.get("title") or _FALLBACK_TITLE
        vocab = result.get("vocab") or _dummy_vocab_format(_FALLBACK_VOCAB_WORDS)

        output = {
            "title": title,
            "sections": sections,
            "vocab": vocab,
            "target_level": reading_level,
            "rationale": result.get("plan_summary", ""),
            "topic_bank_id": bank_topic_id,
        }

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="select_stretch_text",
                input_json=input_json,
                output_json={"title": title, "section_count": len(sections), "vocab_count": len(vocab)},
                error_text=None,
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=result.get("iteration", 0),
            )
        except Exception:
            pass

        return output

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="select_stretch_text",
                input_json=input_json,
                output_json=None,
                error_text=str(exc),
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=0,
            )
        except Exception:
            pass

        # Fallback to dummy content
        return {
            "title": _FALLBACK_TITLE,
            "sections": _FALLBACK_SECTIONS,
            "vocab": _dummy_vocab_format(_FALLBACK_VOCAB_WORDS),
            "target_level": "800L",
            "rationale": f"Fallback due to error: {exc}",
        }
