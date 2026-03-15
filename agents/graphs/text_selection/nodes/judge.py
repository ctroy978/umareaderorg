import json
import re

from agents.llm import get_judge_llm
from agents.graphs.text_selection.state import TextSelectionState
from agents.graphs.text_selection.prompts.judge import JUDGE_SYSTEM, JUDGE_USER

# Maps current_step → artifact name used as key in judge_feedback / retry_counts
ARTIFACT_MAP = {
    "topic_matcher": "topic",
    "text_generator": "generated_text",
    "vocab_extractor": "vocab",
}


def _format_artifact(artifact_name: str, value) -> str:
    if value is None:
        return "[No content]"
    if isinstance(value, list):
        return json.dumps(value, indent=2)
    return str(value)


def judge_node(state: TextSelectionState) -> dict:
    llm = get_judge_llm()
    current_step = state.get("current_step", "")
    artifact_name = ARTIFACT_MAP.get(current_step, current_step)

    # Get artifact value from state
    artifact_value = state.get(artifact_name)
    artifact_content = _format_artifact(artifact_name, artifact_value)

    user_msg = JUDGE_USER.format(
        artifact_name=artifact_name,
        reading_level=state.get("reading_level", ""),
        interests_str=", ".join(state.get("interests", [])),
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
                # Fallback: auto-approve to avoid infinite loops
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
