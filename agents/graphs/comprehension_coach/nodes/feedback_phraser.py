import json
import re

from agents.llm import get_worker_llm
from agents.graphs.comprehension_coach.state import ComprehensionCoachState
from agents.graphs.comprehension_coach.prompts.feedback_phraser import (
    FEEDBACK_PHRASER_SYSTEM,
    FEEDBACK_PHRASER_USER,
)


def feedback_phraser_node(state: ComprehensionCoachState) -> dict:
    llm = get_worker_llm()

    user_msg = FEEDBACK_PHRASER_USER.format(
        student_level=state["student_level"],
        strategy=state["strategy"],
        is_strong=state.get("is_strong"),
        evidence_snippet=state.get("evidence_snippet") or "",
        rationale=state.get("rationale") or "",
    )

    messages = [
        {"role": "system", "content": FEEDBACK_PHRASER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "feedback": parsed["feedback"],
        "current_step": "feedback_phraser",
    }
