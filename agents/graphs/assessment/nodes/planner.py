import json
import re

from agents.llm import get_planner_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.planner import PLANNER_SYSTEM, PLANNER_USER

_VALID_ACTIONS = {"question_generator", "ideal_gist_generator", "end"}


def _status(value) -> str:
    if value is None:
        return "None"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return f"{{...{len(value)} keys}}"
    if isinstance(value, str):
        preview = value[:80].replace("\n", " ")
        return f'"{preview}..."' if len(value) > 80 else f'"{preview}"'
    return str(value)


def _judge_feedback_summary(judge_feedback: dict) -> str:
    if not judge_feedback:
        return "No judge feedback yet."
    lines = []
    for artifact, fb in judge_feedback.items():
        score = fb.get("score", "?")
        lines.append(f"- {artifact}: score={score}/10")
    return "\n".join(lines)


def planner_node(state: AssessmentState) -> dict:
    llm = get_planner_llm()

    user_msg = PLANNER_USER.format(
        mode=state.get("mode", "generate"),
        mastery_questions_status=_status(state.get("mastery_questions")),
        assessment_status=_status(state.get("judge_feedback", {}).get("assessment")),
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
