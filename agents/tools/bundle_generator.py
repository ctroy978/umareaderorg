"""
Orchestrates pre-generation of a full session bundle before the student starts.

Called from session.py via loop.run_in_executor so it runs in a thread pool.
All steps are blocking/synchronous — no async inside this module.

Parallelism strategy:
  Step 1 (text_selection) must finish first — everything depends on its output.
  Steps 2+3 (comp_coach ×4 and mastery questions) are independent of each other
  and run concurrently via ThreadPoolExecutor.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.supabase_client import (
    update_session_bundle,
    fail_session_bundle,
    get_available_strategies,
    get_recent_strategies,
)
from agents.tools.text_selection_tool import select_stretch_text_tool
from agents.tools.comprehension_coach_tool import coach_comprehension_pause
from agents.tools.assessment_tool import generate_mastery_questions
from agents.tools.strategy_selector import select_strategy

_COMP_STRATEGIES = ["main idea", "inference", "question generation", "main idea"]
_STRATEGY_CHUNK_INDEX = 1  # second chunk (0-based) gets the targeted strategy question


def _log(msg: str) -> None:
    print(f"[bundle {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _run_comp_coach(i: int, section: dict, strategy: str, reading_level: str, user_id: str, is_strategy_question: bool = False) -> dict:
    _log(f"comp_coach section {i+1}/4 (strategy='{strategy}'{' [STRATEGY Q]' if is_strategy_question else ''}) starting")
    t0 = time.monotonic()
    result = coach_comprehension_pause(
        text_section=section["text"],
        student_response=None,
        strategy=strategy,
        student_level=reading_level,
        session_id=None,
        student_id=user_id,
    )
    _log(f"comp_coach section {i+1}/4 done in {time.monotonic()-t0:.1f}s")
    return {
        "section_index": i,
        "strategy": strategy,
        "prompt": result["prompt"],
        "rubric": result.get("rationale", ""),
        "is_strategy_question": is_strategy_question,
    }


def _run_mastery(full_text: str, reading_level: str, user_id: str) -> list:
    _log("mastery question generation starting")
    t0 = time.monotonic()
    questions = generate_mastery_questions(
        full_text=full_text,
        reading_level=reading_level,
        session_id=None,
        student_id=user_id,
    )
    _log(f"mastery questions done in {time.monotonic()-t0:.1f}s — {len(questions)} questions")
    return questions


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
    bundle_start = time.monotonic()
    _log(f"START bundle={bundle_id} topic='{topic}' level='{reading_level}'")

    try:
        # ── Step 0: strategy selection ────────────────────────────────────────
        _log("step 0: selecting reading strategy")
        t0 = time.monotonic()
        try:
            available = get_available_strategies(reading_level) or ["Making Inferences"]
            recent = get_recent_strategies(user_id, limit=3)
            session_strategy = select_strategy(topic, reading_level, recent, available)
        except Exception as e:
            _log(f"step 0: strategy selection failed ({e}), using fallback")
            session_strategy = "Making Inferences"
        _log(f"step 0: strategy='{session_strategy}' in {time.monotonic()-t0:.1f}s")

        # ── Step 1: passage + vocab (must complete before anything else) ──────
        _log("step 1/3: text_selection starting")
        t0 = time.monotonic()
        content = select_stretch_text_tool(
            student_id=user_id,
            session_id=None,
            access_token=access_token,
            topic_override=topic,
            strategy_hint=session_strategy,
            strategy_chunk_index=_STRATEGY_CHUNK_INDEX,
        )
        sections = content["sections"]
        title = content["title"]
        vocab = content["vocab"]
        topic_bank_id = content.get("topic_bank_id")
        full_text = "\n\n".join(s["text"] for s in sections)
        _log(
            f"step 1/3: text_selection done in {time.monotonic()-t0:.1f}s"
            f" — '{title}' ({len(sections)} sections, {len(vocab)} vocab)"
        )

        # ── Steps 2+3: comp_coach ×4 and mastery run in parallel ─────────────
        _log("step 2+3: launching comp_coach ×4 and mastery in parallel")
        t0 = time.monotonic()

        comp_results = [None] * len(sections)
        mastery_questions = None

        with ThreadPoolExecutor(max_workers=5) as pool:
            # Submit comp_coach for each section; strategy chunk gets the session strategy
            comp_futures = {
                pool.submit(
                    _run_comp_coach,
                    i,
                    section,
                    session_strategy if i == _STRATEGY_CHUNK_INDEX else _COMP_STRATEGIES[i % len(_COMP_STRATEGIES)],
                    reading_level,
                    user_id,
                    i == _STRATEGY_CHUNK_INDEX,
                ): i
                for i, section in enumerate(sections)
            }
            # Submit mastery generation
            mastery_future = pool.submit(_run_mastery, full_text, reading_level, user_id)

            # Collect comp results in original section order
            for future in as_completed(comp_futures):
                idx = comp_futures[future]
                comp_results[idx] = future.result()

            mastery_questions = mastery_future.result()

        _log(f"step 2+3: parallel phase done in {time.monotonic()-t0:.1f}s")

        # ── Apply safety defaults for new fields ──────────────────────────────
        for q in mastery_questions:
            if q.get("type") == "short_answer":
                q.setdefault("source_span", "")
                q.setdefault("key_points", [])
            elif q.get("type") == "multiple_choice":
                q.setdefault("explanation", "")

        reflection_question = (
            f"If you could ask the author of '{title}' one question, what would it be and why?"
        )

        # ── Persist ───────────────────────────────────────────────────────────
        _log("persisting bundle to database")
        update_session_bundle(
            bundle_id,
            passage_title=title,
            passage_text=full_text,
            passage_sections=sections,
            vocab_questions=vocab,
            comprehension_questions=comp_results,
            mastery_questions=mastery_questions,
            reflection_question=reflection_question,
            topic_bank_id=topic_bank_id,
            strategy_of_session=session_strategy,
            strategy_chunk_index=_STRATEGY_CHUNK_INDEX,
        )

        _log(f"DONE total={time.monotonic()-bundle_start:.1f}s status=ready")

    except Exception as exc:
        _log(f"ERROR after {time.monotonic()-bundle_start:.1f}s: {exc}")
        fail_session_bundle(bundle_id, str(exc))
