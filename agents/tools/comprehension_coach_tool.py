"""
Tool wrapper for the comprehension_coach LangGraph agent.

Called directly as a Python function from session.py (blocking, run in executor).
"""
import time

from app.supabase_client import log_agent_run
from app.data.session_content import READING_PAUSE_PROMPTS

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from agents.graphs.comprehension_coach.graph import build_comprehension_coach_graph
        _graph = build_comprehension_coach_graph()
    return _graph


def coach_comprehension_pause(
    text_section: str,
    student_response: str | None,
    strategy: str,
    student_level: str,
    session_id: str | None,
    student_id: str,
) -> dict:
    """
    Run the comprehension_coach agent.

    When student_response is None: generates a comprehension prompt for the section.
    When student_response is a string: evaluates the response and generates feedback.

    Returns:
        {prompt, feedback, is_strong, evidence_snippet, rationale}

    Falls back to READING_PAUSE_PROMPTS[0] fields on any exception.
    """
    start = time.monotonic()
    mode = "evaluate" if student_response is not None else "generate"
    input_json = {
        "mode": mode,
        "strategy": strategy,
        "student_level": student_level,
        "session_id": session_id,
    }

    try:
        initial_state = {
            "text_section": text_section,
            "student_response": student_response,
            "strategy": strategy,
            "student_level": student_level,
            "generated_prompt": None,
            "is_strong": None,
            "feedback": None,
            "evidence_snippet": None,
            "rationale": None,
            "judge_feedback": {},
            "retry_counts": {},
            "current_step": None,
            "next_action": None,
            "plan_summary": None,
            "iteration": 0,
        }

        graph = _get_graph()
        result = graph.invoke(initial_state)

        output = {
            "prompt": result.get("generated_prompt") or "",
            "feedback": result.get("feedback") or "",
            "is_strong": result.get("is_strong"),
            "evidence_snippet": result.get("evidence_snippet") or "",
            "rationale": result.get("rationale") or "",
        }

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="coach_comprehension_pause",
                input_json=input_json,
                output_json={"mode": mode, "has_prompt": bool(output["prompt"]), "is_strong": output["is_strong"]},
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
                tool_name="coach_comprehension_pause",
                input_json=input_json,
                output_json=None,
                error_text=str(exc),
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=0,
            )
        except Exception:
            pass

        # Fallback to first dummy pause prompt
        fallback = READING_PAUSE_PROMPTS[0]
        return {
            "prompt": fallback["prompt_text"],
            "feedback": fallback["dummy_feedback_good"],
            "is_strong": True,
            "evidence_snippet": "",
            "rationale": f"Fallback due to error: {exc}",
        }
