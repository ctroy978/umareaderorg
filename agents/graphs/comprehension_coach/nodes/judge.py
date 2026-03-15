import json
import re

from agents.llm import get_judge_llm
from agents.graphs.comprehension_coach.state import ComprehensionCoachState
from agents.graphs.comprehension_coach.prompts.judge import JUDGE_SYSTEM, JUDGE_USER

# Maps current_step → artifact name used as key in judge_feedback / retry_counts
ARTIFACT_MAP = {
    "prompt_generator": "generated_prompt",
    "feedback_phraser": "response_assessment",
}


def _format_artifact(artifact_name: str, state: ComprehensionCoachState) -> str:
    if artifact_name == "generated_prompt":
        value = state.get("generated_prompt")
        return str(value) if value is not None else "[No content]"
    elif artifact_name == "response_assessment":
        # Combine is_strong, feedback, evidence_snippet as JSON
        return json.dumps({
            "is_strong": state.get("is_strong"),
            "feedback": state.get("feedback"),
            "evidence_snippet": state.get("evidence_snippet"),
        }, indent=2)
    return "[No content]"


def judge_node(state: ComprehensionCoachState) -> dict:
    llm = get_judge_llm()
    current_step = state.get("current_step", "")
    artifact_name = ARTIFACT_MAP.get(current_step, current_step)

    artifact_content = _format_artifact(artifact_name, state)

    user_msg = JUDGE_USER.format(
        artifact_name=artifact_name,
        strategy=state.get("strategy", ""),
        student_level=state.get("student_level", ""),
        is_strong=state.get("is_strong"),
        artifact_content=artifact_content,
    )

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    parsed = None
    for attempt in range(2):
        try:
            response = llm.invoke(messages)
            content = response.content.strip()
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            parsed = json.loads(content)
            break
        except Exception as e:
            if attempt == 1:
                parsed = {
                    "artifact": artifact_name,
                    "score": 8,
                    "dimensions": {},
                    "issues": [],
                    "instructions": f"Judge parse error: {e}. Auto-approved.",
                }

    current_feedback = dict(state.get("judge_feedback", {}))
    current_retries = dict(state.get("retry_counts", {}))

    current_feedback[artifact_name] = parsed

    if parsed.get("score", 0) < 8:
        current_retries[artifact_name] = current_retries.get(artifact_name, 0) + 1

    return {
        "judge_feedback": current_feedback,
        "retry_counts": current_retries,
    }
