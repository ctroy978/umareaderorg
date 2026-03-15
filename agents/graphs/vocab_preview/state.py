from typing import Optional
from typing_extensions import TypedDict


class VocabPreviewState(TypedDict):
    word: str
    sentence: str
    guess: str
    evaluation: Optional[dict]   # {is_correct, feedback, rationale}
    judge_feedback: dict[str, dict]
    retry_counts: dict[str, int]
    current_step: Optional[str]
    next_action: Optional[str]
    plan_summary: Optional[str]
    iteration: int
