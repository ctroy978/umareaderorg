"""Adaptive reading level adjustment — called after each session completion."""

from app.supabase_client import get_session_responses, upsert_profile

BANDS = ["600L", "800L", "1000L", "1200L"]
BAND_BASES = {"600L": 600, "800L": 800, "1000L": 1000, "1200L": 1200}
BAND_UP_THRESHOLDS = {"600L": 750, "800L": 950, "1000L": 1150}
BAND_DOWN_THRESHOLDS = {"800L": 650, "1000L": 850, "1200L": 1100}
PROMOTION_REQUIRED = 4
DEMOTION_REQUIRED = 6
MIN_SESSIONS_BEFORE_CHANGE = 4
ALPHA = 0.25


def _compute_delta(accuracy: float) -> float:
    if accuracy >= 0.85:
        return 8 + (accuracy - 0.85) * 70
    if accuracy >= 0.70:
        return (accuracy - 0.75) * 30
    if accuracy < 0.55:
        return -6 - (0.55 - accuracy) * 60
    return (accuracy - 0.65) * 20


def _check_band_change(new_current: float, current_band: str, history: list) -> str | None:
    if len(history) < MIN_SESSIONS_BEFORE_CHANGE:
        return None

    band_idx = BANDS.index(current_band)

    # Check promotion
    if current_band in BAND_UP_THRESHOLDS and band_idx < len(BANDS) - 1:
        threshold = BAND_UP_THRESHOLDS[current_band]
        last_n = history[-PROMOTION_REQUIRED:]
        if len(last_n) >= PROMOTION_REQUIRED and all(
            e["current_level"] >= threshold for e in last_n
        ):
            return BANDS[band_idx + 1]

    # Check demotion
    if current_band in BAND_DOWN_THRESHOLDS and band_idx > 0:
        threshold = BAND_DOWN_THRESHOLDS[current_band]
        last_n = history[-DEMOTION_REQUIRED:]
        if len(last_n) >= DEMOTION_REQUIRED and all(
            e["current_level"] <= threshold for e in last_n
        ):
            return BANDS[band_idx - 1]

    return None


def run_level_adjustment(
    student_id: str, session_id: str, profile: dict, access_token: str,
    strategy: str | None = None,
) -> bool:
    """Update current_level and possibly reading_level after a completed session.

    Returns True if the reading_level band changed, False otherwise.
    """
    responses = get_session_responses(session_id)
    scored = [r for r in responses if r.get("is_correct") is not None]
    if not scored:
        return False

    accuracy = sum(1 for r in scored if r["is_correct"]) / len(scored)

    current_band = (profile or {}).get("reading_level", "800L")
    current = (profile or {}).get("current_level") or float(BAND_BASES.get(current_band, 800))

    delta = _compute_delta(accuracy)
    new_current = round(current + ALPHA * delta, 1)

    history: list = list((profile or {}).get("level_history") or [])
    entry: dict = {"current_level": new_current, "session_id": session_id}
    if strategy:
        entry["strategy"] = strategy
    history.append(entry)
    history = history[-10:]

    new_band = _check_band_change(new_current, current_band, history)

    payload: dict = {"current_level": new_current, "level_history": history}
    if new_band:
        payload["reading_level"] = new_band

    upsert_profile(student_id, payload, access_token=access_token)
    return bool(new_band)
