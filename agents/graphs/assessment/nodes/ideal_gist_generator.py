import json
import re

from agents.llm import get_worker_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.ideal_gist_generator import (
    IDEAL_GIST_GENERATOR_SYSTEM,
    IDEAL_GIST_GENERATOR_USER,
)


def ideal_gist_generator_node(state: AssessmentState) -> dict:
    llm = get_worker_llm()

    user_msg = IDEAL_GIST_GENERATOR_USER.format(
        full_text=state["full_text"],
    )

    messages = [
        {"role": "system", "content": IDEAL_GIST_GENERATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "ideal_gist": parsed["ideal_gist"],
        "current_step": "ideal_gist_generator",
    }
