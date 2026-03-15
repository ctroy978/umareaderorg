"""
Orchestrates pre-generation of a full session bundle before the student starts.

Called from session.py via loop.run_in_executor so it runs in a thread pool.
All steps are blocking/synchronous — no async inside this module.
"""
import json

from app.supabase_client import update_session_bundle, fail_session_bundle
from agents.tools.text_selection_tool import select_stretch_text_tool
from agents.tools.comprehension_coach_tool import coach_comprehension_pause
from agents.tools.assessment_tool import generate_mastery_questions

_COMP_STRATEGIES = ["main idea", "inference", "question generation", "main idea"]


def generate_session_bundle(
    bundle_id: str,
    user_id: str,
    topic: str,
    reading_level: str,
    access_token: str | None,
) -> None:
    """
    Generate all session content upfront and persist it to the session_bundles row.

    On any failure, marks the bundle as 'error'.
    """
    try:
        # Step 1: Generate passage + vocab
        content = select_stretch_text_tool(
            student_id=user_id,
            session_id=None,
            access_token=access_token,
            topic_override=topic,
        )
        sections = content["sections"]
        title = content["title"]
        vocab = content["vocab"]
        full_text = "\n\n".join(s["text"] for s in sections)

        # Step 2: Generate comprehension questions (one per section)
        comprehension_questions = []
        for i, section in enumerate(sections):
            strategy = _COMP_STRATEGIES[i % len(_COMP_STRATEGIES)]
            result = coach_comprehension_pause(
                text_section=section["text"],
                student_response=None,
                strategy=strategy,
                student_level=reading_level,
                session_id=None,
                student_id=user_id,
            )
            comprehension_questions.append({
                "section_index": i,
                "strategy": strategy,
                "prompt": result["prompt"],
                "rubric": result.get("rationale", ""),
            })

        # Step 3: Generate mastery questions (2 MC + 1 SA)
        mastery_questions = generate_mastery_questions(
            full_text=full_text,
            reading_level=reading_level,
            session_id=None,
            student_id=user_id,
        )

        # Step 4: Apply safety defaults for new fields
        for q in mastery_questions:
            if q.get("type") == "short_answer":
                q.setdefault("source_span", "")
                q.setdefault("key_points", [])
            elif q.get("type") == "multiple_choice":
                q.setdefault("explanation", "")

        # Step 5: Static reflection question
        reflection_question = (
            f"If you could ask the author of '{title}' one question, what would it be and why?"
        )

        # Step 6: Persist everything
        update_session_bundle(
            bundle_id,
            passage_title=title,
            passage_text=full_text,
            passage_sections=sections,
            vocab_questions=vocab,
            comprehension_questions=comprehension_questions,
            mastery_questions=mastery_questions,
            reflection_question=reflection_question,
        )

    except Exception as exc:
        fail_session_bundle(bundle_id, str(exc))
