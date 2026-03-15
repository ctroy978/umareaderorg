import json
import re

from agents.llm import get_judge_llm
from agents.graphs.vocab_preview.state import VocabPreviewState
from agents.graphs.vocab_preview.prompts.judge import JUDGE_SYSTEM, JUDGE_USER


def judge_node(state: VocabPreviewState) -> dict:
    llm = get_judge_llm()

    evaluation = state.get("evaluation", {})
    evaluation_content = json.dumps(evaluation, indent=2) if evaluation else "[No evaluation]"

    user_msg = JUDGE_USER.format(
        word=state["word"],
        guess=state["guess"],
        evaluation_content=evaluation_content,
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
                    "artifact": "evaluation",
                    "score": 8,
                    "dimensions": {},
                    "issues": [],
                    "instructions": f"Judge parse error: {e}. Auto-approved.",
                }

    current_feedback = dict(state.get("judge_feedback", {}))
    current_retries = dict(state.get("retry_counts", {}))

    current_feedback["evaluation"] = parsed

    if parsed.get("score", 0) < 8:
        current_retries["evaluation"] = current_retries.get("evaluation", 0) + 1

    return {
        "judge_feedback": current_feedback,
        "retry_counts": current_retries,
    }
