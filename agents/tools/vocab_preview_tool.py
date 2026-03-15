"""
Tool wrapper for the vocab_preview LangGraph agent.

Called directly as a Python function from session.py (blocking, run in executor).
"""
import time

from app.supabase_client import log_agent_run

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from agents.graphs.vocab_preview.graph import build_vocab_preview_graph
        _graph = build_vocab_preview_graph()
    return _graph


def evaluate_vocab_guess(word: str, sentence: str, guess: str) -> dict:
    """
    Run the vocab_preview agent to evaluate a student's vocabulary guess.

    Returns:
        {is_correct, feedback, rationale}

    Falls back to a generic approval on any exception.
    """
    start = time.monotonic()
    input_json = {"word": word, "sentence": sentence, "guess": guess}

    try:
        initial_state = {
            "word": word,
            "sentence": sentence,
            "guess": guess,
            "evaluation": None,
            "judge_feedback": {},
            "retry_counts": {},
            "current_step": None,
            "next_action": None,
            "plan_summary": None,
            "iteration": 0,
        }

        graph = _get_graph()
        result = graph.invoke(initial_state)

        evaluation = result.get("evaluation") or {
            "is_correct": True,
            "feedback": "Great effort! Let's keep going.",
            "rationale": "No evaluation produced — fallback used.",
        }

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id="unknown",
                tool_name="evaluate_vocab_guess",
                input_json=input_json,
                output_json={"is_correct": evaluation.get("is_correct")},
                error_text=None,
                duration_ms=duration_ms,
                session_id=None,
                iteration_count=result.get("iteration", 0),
            )
        except Exception:
            pass

        return evaluation

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id="unknown",
                tool_name="evaluate_vocab_guess",
                input_json=input_json,
                output_json=None,
                error_text=str(exc),
                duration_ms=duration_ms,
                session_id=None,
                iteration_count=0,
            )
        except Exception:
            pass

        return {
            "is_correct": True,
            "feedback": "Great effort! Let's keep going.",
            "rationale": f"Fallback due to error: {exc}",
        }
