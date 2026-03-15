from typing import Optional
from typing_extensions import TypedDict


class TextSelectionState(TypedDict):
    student_id: str
    reading_level: str
    interests: list[str]
    topic: Optional[str]
    generated_text: Optional[str]   # JSON string: [{"section": int, "text": str}, ...]
    title: Optional[str]
    vocab: Optional[list[dict]]     # [{word, sentence, parallel_sentence}]
    judge_feedback: dict[str, dict]
    retry_counts: dict[str, int]
    current_step: Optional[str]
    next_action: Optional[str]
    plan_summary: Optional[str]
    iteration: int
