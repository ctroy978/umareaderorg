import json
import re

from agents.llm import get_worker_llm
from agents.graphs.text_selection.state import TextSelectionState
from agents.graphs.text_selection.prompts.topic_matcher import (
    TOPIC_MATCHER_SYSTEM,
    TOPIC_MATCHER_USER,
    JUDGE_FEEDBACK_SECTION,
)


def topic_matcher_node(state: TextSelectionState) -> dict:
    llm = get_worker_llm()

    # Build judge feedback section if previous attempt was scored < 8
    judge_feedback_section = ""
    feedback = state.get("judge_feedback", {}).get("topic")
    if feedback and feedback.get("score", 10) < 8:
        judge_feedback_section = JUDGE_FEEDBACK_SECTION.format(
            score=feedback["score"],
            instructions=feedback.get("instructions", "Improve quality."),
        )

    user_msg = TOPIC_MATCHER_USER.format(
        reading_level=state["reading_level"],
        interests_str=", ".join(state.get("interests", [])),
        judge_feedback_section=judge_feedback_section,
    )

    messages = [
        {"role": "system", "content": TOPIC_MATCHER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "topic": parsed["topic"],
        "current_step": "topic_matcher",
    }
