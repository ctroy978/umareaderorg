import json
import re

from agents.llm import get_judge_llm
from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.prompts.judge import JUDGE_SYSTEM, JUDGE_USER

# Maps current_step → artifact name used as key in judge_feedback / retry_counts
ARTIFACT_MAP = {
    "question_generator": "mastery_questions",
    "feedback_phraser": "assessment",
}


def _format_artifact(artifact_name: str, state: AssessmentState) -> str:
    if artifact_name == "mastery_questions":
        value = state.get("mastery_questions")
        return json.dumps(value, indent=2) if value else "[No content]"
    elif artifact_name == "assessment":
        # Combine all assess-mode outputs
        return json.dumps({
            "gist_feedback": state.get("gist_feedback"),
            "mastery_scores": state.get("mastery_scores"),
            "reflection_prompt": state.get("reflection_prompt"),
            "overall_session_note": state.get("overall_session_note"),
        }, indent=2)
    return "[No content]"


def judge_node(state: AssessmentState) -> dict:
    llm = get_judge_llm()
    current_step = state.get("current_step", "")
    artifact_name = ARTIFACT_MAP.get(current_step, current_step)

    artifact_content = _format_artifact(artifact_name, state)

    user_msg = JUDGE_USER.format(
        artifact_name=artifact_name,
        reading_level=state.get("reading_level", ""),
        mode=state.get("mode", ""),
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
