from typing import Optional
from typing_extensions import TypedDict


class AssessmentState(TypedDict):
    mode: str                              # "generate" | "assess"
    full_text: str                         # "\n\n".join(s["text"] for s in sections)
    reading_level: str

    # assess mode inputs
    gist: Optional[str]
    mastery_answers: Optional[list[dict]]  # [{question, answer, type, is_correct?}]

    # generate mode output
    mastery_questions: Optional[list[dict]]  # [{id, type, text, choices?, correct_index?}]

    # assess mode outputs
    ideal_gist: Optional[str]
    coverage_analysis: Optional[dict]
    mastery_scores: Optional[list[dict]]   # [{question, correct, feedback}]
    gist_feedback: Optional[dict]          # {praise, also_note}
    reflection_prompt: Optional[str]
    overall_session_note: Optional[str]

    # Standard control fields
    judge_feedback: dict[str, dict]
    retry_counts: dict[str, int]
    current_step: Optional[str]
    next_action: Optional[str]
    plan_summary: Optional[str]
    iteration: int
