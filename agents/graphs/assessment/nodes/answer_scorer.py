import json
import re

from agents.llm import get_worker_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.answer_scorer import (
    ANSWER_SCORER_SYSTEM,
    ANSWER_SCORER_USER,
)


def answer_scorer_node(state: AssessmentState) -> dict:
    llm = get_worker_llm()

    mastery_answers = state.get("mastery_answers") or []

    user_msg = ANSWER_SCORER_USER.format(
        full_text=state["full_text"],
        mastery_answers_json=json.dumps(mastery_answers, indent=2),
    )

    messages = [
        {"role": "system", "content": ANSWER_SCORER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "mastery_scores": parsed["mastery_scores"],
        "current_step": "answer_scorer",
    }
