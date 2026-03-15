import json
import re

from agents.llm import get_worker_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.coverage_analyzer import (
    COVERAGE_ANALYZER_SYSTEM,
    COVERAGE_ANALYZER_USER,
)


def coverage_analyzer_node(state: AssessmentState) -> dict:
    llm = get_worker_llm()

    user_msg = COVERAGE_ANALYZER_USER.format(
        ideal_gist=state.get("ideal_gist") or "",
        gist=state.get("gist") or "",
    )

    messages = [
        {"role": "system", "content": COVERAGE_ANALYZER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "coverage_analysis": parsed,
        "current_step": "coverage_analyzer",
    }
