import json
import re

from agents.llm import get_planner_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.question_generator import (
    QUESTION_GENERATOR_SYSTEM,
    QUESTION_GENERATOR_USER,
)


def question_generator_node(state: AssessmentState) -> dict:
    # Use 70B planner model for higher quality question generation
    llm = get_planner_llm()

    user_msg = QUESTION_GENERATOR_USER.format(
        full_text=state["full_text"],
        reading_level=state["reading_level"],
    )

    messages = [
        {"role": "system", "content": QUESTION_GENERATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "mastery_questions": parsed["mastery_questions"],
        "current_step": "question_generator",
    }
