import json
import re

from agents.llm import get_worker_llm
from agents.graphs.comprehension_coach.state import ComprehensionCoachState
from agents.graphs.comprehension_coach.prompts.prompt_generator import (
    PROMPT_GENERATOR_SYSTEM,
    PROMPT_GENERATOR_USER,
)


def prompt_generator_node(state: ComprehensionCoachState) -> dict:
    llm = get_worker_llm()

    user_msg = PROMPT_GENERATOR_USER.format(
        text_section=state["text_section"],
        strategy=state["strategy"],
        student_level=state["student_level"],
    )

    messages = [
        {"role": "system", "content": PROMPT_GENERATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "generated_prompt": parsed["prompt"],
        "rationale": parsed.get("rationale", ""),
        "current_step": "prompt_generator",
    }
