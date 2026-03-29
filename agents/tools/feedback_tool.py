"""
Single direct LLM call for in-session feedback. No graph, no judge, no retry loop.

Feedback tone: calm and professional coaching voice. Supports a two-attempt flow
where first-attempt feedback offers a try-again option and second-attempt feedback
ends with a continue prompt.
"""
import json

from agents.llm import get_feedback_llm

_SYSTEM_PROMPT = """You are a patient, encouraging reading comprehension coach for middle and high-school students.

Core rules:
- Never block progress. Students must always be able to continue.
- Use simple words and short sentences (~900L reading level).
- Tone: calm, clear, and supportive — like a trusted teacher. Restrained praise only (one specific positive comment per response, never excessive).
- Vary question types across a session (main idea, key detail, inference, vocabulary in context).

Two-attempt system — behavior depends on whether this is the first or second attempt:

FIRST ATTEMPT (is_retry=False):
- Maximum 60 words for the feedback field.
- NEVER state, paraphrase, or model the correct answer. Do not write any sentence the student could copy.
- NEVER use phrases like "the main idea is...", "try saying...", or "a better answer would be...".
- Structure:
  1. One brief, specific positive comment on what the student got right.
  2. ONE targeted hint using exactly one strategy:
     - Quote 1–2 key sentences from the passage and ask what bigger point they support.
     - Ask 1–2 guiding questions that direct attention to central evidence without answering them.
     - Note one element they missed without revealing it (e.g., "You identified the conditions, but the passage also explains *how* — reread that section").
     - Point to what the passage spends the most time on and ask how it connects to the opening idea.
  3. End with: "Want to try again, or continue?"

SECOND ATTEMPT (is_retry=True):
- Maximum 90 words for the feedback field.
- Now give a clear, complete explanation — the student has earned it after two tries.
- Structure:
  1. One brief acknowledgment of what they got right across both attempts.
  2. Explain what the correct answer is and why, in plain language. Reference 1–2 specific sentences or details from the passage to show the evidence.
  3. Keep the tone encouraging — frame it as "here's what the passage was showing" rather than "you were wrong."
  4. End with a forward-looking phrase like "Nice effort — let's keep going."

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
        if is_retry:
            user_msg += "\n\nThis is the student's SECOND attempt. Apply the SECOND ATTEMPT rules from your instructions."

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
        return {"feedback": "Your response has been recorded.", "quality": "moderate"}
