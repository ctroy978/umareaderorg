import json
import re

from agents.llm import get_planner_llm
from agents.graphs.vocab_preview.state import VocabPreviewState
from agents.graphs.vocab_preview.prompts.planner import PLANNER_SYSTEM, PLANNER_USER

_VALID_ACTIONS = {"evaluator", "end"}


def _status(value) -> str:
    if value is None:
        return "None"
    if isinstance(value, dict):
        return f"{{is_correct: {value.get('is_correct')}, ...}}"
    return str(value)


def _judge_feedback_summary(judge_feedback: dict) -> str:
    if not judge_feedback:
        return "No judge feedback yet."
    lines = []
    for artifact, fb in judge_feedback.items():
        score = fb.get("score", "?")
        lines.append(f"- {artifact}: score={score}/10")
    return "\n".join(lines)


def planner_node(state: VocabPreviewState) -> dict:
    llm = get_planner_llm()

    user_msg = PLANNER_USER.format(
        evaluation_status=_status(state.get("evaluation")),
        judge_feedback_summary=_judge_feedback_summary(state.get("judge_feedback", {})),
        retry_counts=json.dumps(state.get("retry_counts", {})),
        iteration=state.get("iteration", 0),
    )

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    next_action = parsed["next_action"]
    if next_action not in _VALID_ACTIONS:
        raise ValueError(
            f"Planner returned invalid next_action '{next_action}'. "
            f"Valid: {sorted(_VALID_ACTIONS)}"
        )

    return {
        "next_action": next_action,
        "current_step": parsed.get("current_step", next_action),
        "plan_summary": parsed.get("plan_summary", ""),
        "iteration": state.get("iteration", 0) + 1,
    }
