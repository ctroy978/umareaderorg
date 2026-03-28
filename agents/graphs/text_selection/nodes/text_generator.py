import json
import re

from agents.llm import get_planner_llm
from agents.graphs.text_selection.state import TextSelectionState
from agents.graphs.text_selection.prompts.text_generator import (
    TEXT_GENERATOR_SYSTEM,
    TEXT_GENERATOR_USER,
    JUDGE_FEEDBACK_SECTION,
    STRATEGY_HINT_SECTION,
)


def text_generator_node(state: TextSelectionState) -> dict:
    llm = get_planner_llm()  # 70B for quality writing

    judge_feedback_section = ""
    feedback = state.get("judge_feedback", {}).get("generated_text")
    if feedback and feedback.get("score", 10) < 8:
        judge_feedback_section = JUDGE_FEEDBACK_SECTION.format(
            score=feedback["score"],
            instructions=feedback.get("instructions", "Improve quality."),
        )

    strategy_hint_section = ""
    strategy_hint = state.get("strategy_hint")
    if strategy_hint:
        chunk_idx = state.get("strategy_chunk_index") or 1
        strategy_hint_section = STRATEGY_HINT_SECTION.format(
            section_number=chunk_idx + 1,
            strategy=strategy_hint,
        )

    user_msg = TEXT_GENERATOR_USER.format(
        topic=state["topic"],
        reading_level=state["reading_level"],
        strategy_hint_section=strategy_hint_section,
        judge_feedback_section=judge_feedback_section,
    )

    messages = [
        {"role": "system", "content": TEXT_GENERATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "generated_text": json.dumps(parsed["sections"]),
        "title": parsed["title"],
        "current_step": "text_generator",
    }
