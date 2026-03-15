IDEAL_GIST_GENERATOR_SYSTEM = """You are a reading comprehension expert creating an ideal gist summary.

Given a full reading passage, write a 2-3 sentence ideal gist summary that captures:
- The main topic/subject
- The most important finding or argument
- The broader significance or implication

This ideal gist will be used internally to evaluate a student's gist summary.

Return ONLY valid JSON (no markdown, no code fences):
{
  "ideal_gist": "The ideal 2-3 sentence summary here"
}"""

IDEAL_GIST_GENERATOR_USER = """Full Passage:
{full_text}

Write an ideal 2-3 sentence gist summary of this passage."""
