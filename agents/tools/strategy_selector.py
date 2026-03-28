"""
Selects the best reading comprehension strategy for a session.

Uses a single lightweight LLM call to pick the strategy that best fits the
topic, while rotating away from recently used strategies. Falls back to the
least-recently-used strategy from the available list if the LLM call fails.
"""
import json
import re

from agents.llm import get_worker_llm

# One-sentence description used in the LLM prompt for each strategy name.
# Keys must exactly match the strategy names stored in strategy_lessons.
_STRATEGY_DESCRIPTIONS = {
    "Summarizing": (
        "Best for dense informational text with multiple key facts, complex "
        "cause-effect chains, or passages that cover several distinct ideas."
    ),
    "Making Inferences": (
        "Best for topics where important conclusions are implied rather than "
        "stated — science explanations, historical motivations, or any passage "
        "where 'reading between the lines' is rewarding."
    ),
    "Text Structure": (
        "Best for topics naturally organized around compare/contrast, "
        "problem/solution, or cause/effect — history, policy, engineering, "
        "or any subject with a clear rhetorical pattern."
    ),
}

_FALLBACK_STRATEGY = "Making Inferences"


def _least_recently_used(available: list[str], recent: list[str]) -> str:
    """Return the strategy from available that was used least recently."""
    not_recent = [s for s in available if s not in recent]
    if not_recent:
        return not_recent[0]
    # All have been used recently — pick the one used longest ago
    for s in reversed(recent):
        if s in available:
            return s
    return available[0]


def select_strategy(
    topic: str,
    reading_level: str,
    recent_strategies: list[str],
    available_strategies: list[str],
) -> str:
    """
    Pick the best reading strategy for this session.

    Args:
        topic: The topic/category the student chose (e.g., "space and astronomy").
        reading_level: Student's current level (e.g., "800L").
        recent_strategies: Last 2-3 strategy names used by this student (most recent first).
        available_strategies: Strategy names that have lessons in the DB for this level.

    Returns:
        A strategy string that matches one of the available_strategies entries.
        Falls back to least-recently-used if the LLM call fails or returns an invalid choice.
    """
    if not available_strategies:
        return _FALLBACK_STRATEGY

    if len(available_strategies) == 1:
        return available_strategies[0]

    # Build descriptions for available strategies only
    strategy_lines = []
    for s in available_strategies:
        desc = _STRATEGY_DESCRIPTIONS.get(s, "A reading comprehension strategy.")
        strategy_lines.append(f'  - "{s}": {desc}')
    strategies_block = "\n".join(strategy_lines)

    recent_block = (
        ", ".join(f'"{s}"' for s in recent_strategies)
        if recent_strategies
        else "none"
    )

    system_prompt = (
        "You are an expert reading coach selecting one reading strategy for a student's session.\n\n"
        "Choose the strategy that will be most useful and engaging given the topic. "
        "Avoid repeating recently used strategies unless there is no other option.\n\n"
        "Return ONLY valid JSON (no markdown, no code fences):\n"
        '{"strategy": "chosen strategy name", "reason": "one sentence justification"}'
    )

    user_prompt = (
        f"Topic: {topic}\n"
        f"Student reading level: {reading_level}\n\n"
        f"Available strategies:\n{strategies_block}\n\n"
        f"Recently used strategies (avoid repeating): {recent_block}\n\n"
        "Choose one strategy from the available list."
    )

    try:
        llm = get_worker_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content)
        chosen = parsed.get("strategy", "").strip()
        if chosen in available_strategies:
            return chosen
    except Exception:
        pass

    # Fallback: pick the strategy least recently used
    return _least_recently_used(available_strategies, recent_strategies)
