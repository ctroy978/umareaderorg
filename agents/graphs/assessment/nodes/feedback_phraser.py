import json
import re

from agents.llm import get_worker_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.feedback_phraser import (
    FEEDBACK_PHRASER_SYSTEM,
    FEEDBACK_PHRASER_USER,
)


def feedback_phraser_node(state: AssessmentState) -> dict:
    llm = get_worker_llm()

    coverage = state.get("coverage_analysis") or {}

    user_msg = FEEDBACK_PHRASER_USER.format(
        full_text=state["full_text"],
        ideal_gist=state.get("ideal_gist") or "",
        gist=state.get("gist") or "",
        covered_ideas=json.dumps(coverage.get("covered_ideas", [])),
        missed_ideas=json.dumps(coverage.get("missed_ideas", [])),
        coverage_score=coverage.get("coverage_score", 5),
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
        "gist_feedback": parsed["gist_feedback"],
        "reflection_prompt": parsed.get("reflection_prompt", ""),
        "overall_session_note": parsed.get("overall_session_note", ""),
        "current_step": "feedback_phraser",
    }
