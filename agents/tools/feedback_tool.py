"""
Single direct LLM call for in-session feedback. No graph, no judge, no retry loop.

Feedback tone: calm and professional coaching voice. Gist section is single-attempt
only (student works from memory, text is not available).
"""
import json

from agents.llm import get_feedback_llm

_SYSTEM_PROMPT = """You are a patient, encouraging reading comprehension coach for middle and high-school students.

Core rules:
- Never block progress. Students must always be able to continue.
- Use simple words and short sentences (~900L reading level).
- Tone: calm, clear, and supportive — like a trusted teacher. Restrained praise only (one specific positive comment per response, never excessive).
- Vary question types across a session (main idea, key detail, inference, vocabulary in context).

GIST SUMMARY FEEDBACK (single attempt — student is working from memory, text is not available):
- Maximum 75 words for the feedback field.
- NEVER suggest the student reread the text, go back, look back, or review the passage. The text is not available to them. Do not use phrases like "reread", "go back to", "look back at", "review the passage", or any equivalent.
- NEVER state, paraphrase, or model the correct answer. Do not write any sentence the student could copy.
- NEVER use phrases like "the main idea is...", "try saying...", or "a better answer would be...".
- First assess quality, then write feedback based on that quality:
  - good: One specific comment affirming what the student captured well. End with "Nice effort — let's keep going." Do NOT add a hint or probing question — the summary is complete.
  - moderate or poor: (1) One brief positive comment on what the student got right. (2) ONE targeted hint using exactly one strategy: quote 1–2 key sentences and ask what bigger point they support; ask 1–2 guiding questions directing attention to central evidence; note one missed element without revealing it; or point to what the passage spends the most time on and ask how it connects to the opening idea. (3) End with "Nice effort — let's keep going."
  - nonsense: Gently redirect them to summarize what they remember from the passage, without judgment.

COMPREHENSION AND SHORT-ANSWER FEEDBACK (may have text available):
- Maximum 70 words for the feedback field.
- First assess quality, then write feedback based on that quality:
  - good: One specific comment affirming what the student captured. End with a brief forward-looking phrase like "Nice work — let's keep going." Do NOT add a probing question or hint — the answer is complete.
  - moderate or poor: (1) One brief positive comment on what the student got right. (2) ONE targeted guiding question pointing toward what they missed, without revealing the answer. (3) End with "Want to try again, or continue?"
  - nonsense: Gently redirect them to the question and passage without judgment.

OUTPUT FORMAT — you must always respond with a JSON object and nothing else:
{
  "feedback": "<your coaching response following the rules above>",
  "quality": "<one of: good, moderate, poor, nonsense>"
}

Quality definitions (assess the student's answer, not their effort):
- good: answer clearly addresses the question and demonstrates genuine comprehension
- moderate: answer partially addresses the question, shows some understanding but misses key points
- poor: answer shows limited comprehension, misses the core idea
- nonsense: off-topic, "I don't know", refuses to engage, or clearly irrelevant

Output ONLY the JSON object. No other text before or after it.
"""

_TEMPLATES = {
    "comprehension": """Section text:
{section_text}

Question asked: {question}

Evaluation criteria: {rubric}

Student's response: {student_response}

Give feedback on this comprehension response.""",

    "gist": """Full passage:
{full_passage}

Student's gist summary: {student_gist}

Give feedback on this summary. Does it capture the main idea? What did they get right or miss?""",

    "mastery_sa": """Question: {question}

Key passage excerpt relevant to this question: {source_span}

Key points a complete answer should cover: {key_points}

Student's answer: {student_answer}

Give feedback on this short answer response.""",
}


def get_feedback(feedback_type: str, is_retry: bool = False, **context) -> dict:
    """
    Get feedback for a student response.

    feedback_type: 'comprehension', 'gist', or 'mastery_sa'
    is_retry: True if this is the student's second attempt on this question
    context: keyword args matching the template placeholders for the given type

    Returns a dict with keys:
      'feedback' (str): coaching text to display to the student
      'quality'  (str): one of 'good', 'moderate', 'poor', 'nonsense' — used for rubric scoring
    Falls back to a neutral message with quality='moderate' on error.
    """
    try:
        template = _TEMPLATES[feedback_type]
        user_msg = template.format(**context)
        if feedback_type == 'gist':
            user_msg += "\n\nIMPORTANT: The student cannot see the passage. Do NOT suggest rereading. Apply the GIST SUMMARY FEEDBACK rules."
        elif is_retry:
            user_msg += "\n\nThis is the student's SECOND and final attempt. Apply the COMPREHENSION AND SHORT-ANSWER FEEDBACK rules, but end with a forward-looking phrase like 'Nice effort — let\\'s keep going.' instead of 'Want to try again, or continue?' — the student has no more tries."

        llm = get_feedback_llm()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        response = llm.invoke(messages)
        raw = response.content.strip()
        parsed = json.loads(raw)
        quality = parsed.get("quality", "moderate")
        if quality not in ("good", "moderate", "poor", "nonsense"):
            quality = "moderate"
        return {"feedback": parsed.get("feedback", "Your response has been recorded."), "quality": quality}
    except Exception:
        raise
