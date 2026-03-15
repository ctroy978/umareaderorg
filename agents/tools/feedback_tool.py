"""
Single direct Grok call for in-session feedback. No graph, no judge, no retry.

Feedback tone: analytical, not encouraging. Never uses "Great job!", "Well done!",
"Excellent!", or "Nice work!". Explains specifically why a response is strong or
where it falls short, referencing passage text when relevant.
"""
from agents.llm import get_feedback_llm

_SYSTEM_PROMPT = """You are a reading coach giving feedback to a middle school student.

Rules:
- Never use "Great job!", "Well done!", "Excellent!", "Nice work!", or similar praise phrases.
- Explain specifically why the response is strong or where it falls short.
- Reference the passage text or the question when relevant.
- Write 2-4 sentences in plain language appropriate for a middle school student.
- Analytical tone: focus on what the student did or missed, not on how they feel.
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


def get_feedback(feedback_type: str, **context) -> str:
    """
    Get analytical feedback for a student response.

    feedback_type: 'comprehension', 'gist', or 'mastery_sa'
    context: keyword args matching the template placeholders for the given type

    Returns plain text feedback string. Falls back to a neutral message on error.
    """
    try:
        template = _TEMPLATES[feedback_type]
        user_msg = template.format(**context)

        llm = get_feedback_llm()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception:
        return "Your response has been recorded."
