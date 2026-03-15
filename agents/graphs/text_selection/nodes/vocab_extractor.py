import json
import re

from agents.llm import get_worker_llm
from agents.graphs.text_selection.state import TextSelectionState
from agents.graphs.text_selection.prompts.vocab_extractor import (
    VOCAB_EXTRACTOR_SYSTEM,
    VOCAB_EXTRACTOR_USER,
    JUDGE_FEEDBACK_SECTION,
)


def vocab_extractor_node(state: TextSelectionState) -> dict:
    llm = get_worker_llm()

    # Flatten sections into a readable passage
    sections = json.loads(state["generated_text"])
    passage_text = "\n\n".join(
        f"[Section {s['section']}]\n{s['text']}" for s in sections
    )

    judge_feedback_section = ""
    feedback = state.get("judge_feedback", {}).get("vocab")
    if feedback and feedback.get("score", 10) < 8:
        judge_feedback_section = JUDGE_FEEDBACK_SECTION.format(
            score=feedback["score"],
            instructions=feedback.get("instructions", "Improve quality."),
        )

    user_msg = VOCAB_EXTRACTOR_USER.format(
        passage_text=passage_text,
        judge_feedback_section=judge_feedback_section,
    )

    messages = [
        {"role": "system", "content": VOCAB_EXTRACTOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    parsed = json.loads(content)

    return {
        "vocab": parsed["vocab"],
        "current_step": "vocab_extractor",
    }
