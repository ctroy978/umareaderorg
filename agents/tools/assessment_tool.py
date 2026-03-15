"""
Tool wrapper for the assessment LangGraph agent.

Called directly as a Python function from session.py (blocking, run in executor).
"""
import time

from app.supabase_client import log_agent_run
from app.data.session_content import (
    GIST_FEEDBACK as _FALLBACK_GIST_FEEDBACK,
    MASTERY_QUESTIONS as _FALLBACK_MASTERY_QUESTIONS,
    REFLECTION_PROMPT as _FALLBACK_REFLECTION_PROMPT,
)

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from agents.graphs.assessment.graph import build_assessment_graph
        _graph = build_assessment_graph()
    return _graph


def generate_mastery_questions(
    full_text: str,
    reading_level: str,
    session_id: str | None,
    student_id: str,
) -> list[dict]:
    """
    Run the assessment agent in generate mode to produce 3 mastery questions.

    Returns list of question dicts (2 MC + 1 SA).
    Falls back to list(MASTERY_QUESTIONS) on error or invalid output.
    """
    start = time.monotonic()
    input_json = {"mode": "generate", "reading_level": reading_level, "session_id": session_id}

    try:
        initial_state = {
            "mode": "generate",
            "full_text": full_text,
            "reading_level": reading_level,
            "gist": None,
            "mastery_answers": None,
            "mastery_questions": None,
            "ideal_gist": None,
            "coverage_analysis": None,
            "mastery_scores": None,
            "gist_feedback": None,
            "reflection_prompt": None,
            "overall_session_note": None,
            "judge_feedback": {},
            "retry_counts": {},
            "current_step": None,
            "next_action": None,
            "plan_summary": None,
            "iteration": 0,
        }

        graph = _get_graph()
        result = graph.invoke(initial_state)

        questions = result.get("mastery_questions")

        # Validate: must have 2 MC + 1 SA
        if questions:
            mc = [q for q in questions if q.get("type") == "multiple_choice"]
            sa = [q for q in questions if q.get("type") == "short_answer"]
            if len(mc) != 2 or len(sa) != 1:
                raise ValueError(
                    f"Invalid question distribution: {len(mc)} MC, {len(sa)} SA (expected 2 MC + 1 SA)"
                )
        else:
            raise ValueError("No questions generated")

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="generate_mastery_questions",
                input_json=input_json,
                output_json={"question_count": len(questions)},
                error_text=None,
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=result.get("iteration", 0),
            )
        except Exception:
            pass

        return questions

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="generate_mastery_questions",
                input_json=input_json,
                output_json=None,
                error_text=str(exc),
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=0,
            )
        except Exception:
            pass

        return list(_FALLBACK_MASTERY_QUESTIONS)


def assess_gist_and_mastery(
    full_text: str,
    gist: str,
    mastery_answers: list[dict],
    session_id: str | None,
    student_id: str,
) -> dict:
    """
    Run the assessment agent in assess mode to evaluate gist and mastery answers.

    Returns:
        {gist_feedback, mastery_scores, reflection_prompt, overall_session_note}

    Falls back to GIST_FEEDBACK, REFLECTION_PROMPT from session_content.py on error.
    """
    start = time.monotonic()
    input_json = {
        "mode": "assess",
        "session_id": session_id,
        "answer_count": len(mastery_answers),
    }

    try:
        initial_state = {
            "mode": "assess",
            "full_text": full_text,
            "reading_level": "800L",
            "gist": gist,
            "mastery_answers": mastery_answers,
            "mastery_questions": None,
            "ideal_gist": None,
            "coverage_analysis": None,
            "mastery_scores": None,
            "gist_feedback": None,
            "reflection_prompt": None,
            "overall_session_note": None,
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
            "gist_feedback": result.get("gist_feedback") or _FALLBACK_GIST_FEEDBACK,
            "mastery_scores": result.get("mastery_scores") or [],
            "reflection_prompt": result.get("reflection_prompt") or _FALLBACK_REFLECTION_PROMPT,
            "overall_session_note": result.get("overall_session_note") or "",
        }

        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            log_agent_run(
                student_id=student_id,
                tool_name="assess_gist_and_mastery",
                input_json=input_json,
                output_json={
                    "has_gist_feedback": bool(output["gist_feedback"]),
                    "mastery_score_count": len(output["mastery_scores"]),
                },
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
                tool_name="assess_gist_and_mastery",
                input_json=input_json,
                output_json=None,
                error_text=str(exc),
                duration_ms=duration_ms,
                session_id=session_id,
                iteration_count=0,
            )
        except Exception:
            pass

        return {
            "gist_feedback": _FALLBACK_GIST_FEEDBACK,
            "mastery_scores": [],
            "reflection_prompt": _FALLBACK_REFLECTION_PROMPT,
            "overall_session_note": "",
        }
