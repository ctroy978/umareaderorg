import json
import re

from agents.llm import get_worker_llm
from agents.graphs.comprehension_coach.state import ComprehensionCoachState
from agents.graphs.comprehension_coach.prompts.response_evaluator import (
    RESPONSE_EVALUATOR_SYSTEM,
    RESPONSE_EVALUATOR_USER,
)


def response_evaluator_node(state: ComprehensionCoachState) -> dict:
    llm = get_worker_llm()

    user_msg = RESPONSE_EVALUATOR_USER.format(
        text_section=state["text_section"],
        generated_prompt=state.get("generated_prompt") or "(no specific prompt)",
        student_response=state.get("student_response") or "",
    )

    messages = [
        {"role": "system", "content": RESPONSE_EVALUATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "is_strong": bool(parsed["is_strong"]),
        "evidence_snippet": parsed.get("evidence_snippet", ""),
        "rationale": parsed.get("rationale", ""),
        "current_step": "response_evaluator",
    }
