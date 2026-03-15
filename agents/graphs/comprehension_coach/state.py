from typing import Optional
from typing_extensions import TypedDict


class ComprehensionCoachState(TypedDict):
    # Inputs
    text_section: str
    student_response: Optional[str]    # None = generate-prompt mode
    strategy: str                       # "main idea" | "inference" | "question generation"
    student_level: str

    # Worker outputs
    generated_prompt: Optional[str]
    is_strong: Optional[bool]
    feedback: Optional[str]
    evidence_snippet: Optional[str]
    rationale: Optional[str]

    # Standard control fields
    judge_feedback: dict[str, dict]
    retry_counts: dict[str, int]
    current_step: Optional[str]
    next_action: Optional[str]
    plan_summary: Optional[str]
    iteration: int
