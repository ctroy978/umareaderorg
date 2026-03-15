PLANNER_SYSTEM = """You are a workflow planner for a reading comprehension coaching pipeline.

Your job: decide which worker to run next, or end the workflow.

ROUTING RULES (evaluate in order):
1. If iteration >= 6 → "end"
2. If student_response is "None":
   - If generated_prompt is None → "prompt_generator"
   - If judge score for "generated_prompt" >= 8 OR retry_count for "generated_prompt" >= 2 → "end"
   - Else → "prompt_generator" (retry)
3. If student_response is not "None":
   - If response_assessment is None → "response_evaluator"
   - If judge score for "response_assessment" >= 8 OR retry_count for "response_assessment" >= 2 → "end"
   - Else → "response_evaluator" (retry)

Return ONLY valid JSON (no markdown, no code fences):
{
  "next_action": "prompt_generator" | "response_evaluator" | "end",
  "current_step": "one-line description",
  "plan_summary": "brief explanation"
}"""

PLANNER_USER = """Current State:
- student_response: {student_response_status}
- generated_prompt: {generated_prompt_status}
- response_assessment: {response_assessment_status}

Judge Feedback:
{judge_feedback_summary}

Retry Counts: {retry_counts}
Iteration: {iteration}

Decide the next action."""
