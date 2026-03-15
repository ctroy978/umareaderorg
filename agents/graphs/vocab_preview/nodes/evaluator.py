import json
import re

from agents.llm import get_worker_llm
from agents.graphs.vocab_preview.state import VocabPreviewState
from agents.graphs.vocab_preview.prompts.evaluator import (
    EVALUATOR_SYSTEM,
    EVALUATOR_USER,
    JUDGE_FEEDBACK_SECTION,
)


def evaluator_node(state: VocabPreviewState) -> dict:
    llm = get_worker_llm()

    judge_feedback_section = ""
    feedback = state.get("judge_feedback", {}).get("evaluation")
    if feedback and feedback.get("score", 10) < 8:
        judge_feedback_section = JUDGE_FEEDBACK_SECTION.format(
            score=feedback["score"],
            instructions=feedback.get("instructions", "Improve the evaluation."),
        )

    user_msg = EVALUATOR_USER.format(
        word=state["word"],
        sentence=state["sentence"],
        guess=state["guess"],
        judge_feedback_section=judge_feedback_section,
    )

    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "evaluation": parsed,
        "current_step": "evaluator",
    }
