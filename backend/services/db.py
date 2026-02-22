import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

from services.whatsapp import send_text

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_raw_frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").strip()
if _raw_frontend_url and "://" not in _raw_frontend_url:
    _raw_frontend_url = f"https://{_raw_frontend_url}"
FRONTEND_URL = _raw_frontend_url.rstrip("/")
PRO_MONTHLY_PRICE_INR = 99

PRO_ACTIVE_STATUSES = {"active"}
SUBSCRIPTION_LOCKED_STATUSES = {"free", "expired", "cancelled", "halted", "completed", "paused"}
BODY_WEIGHT_MIN_KG = 25.0
BODY_WEIGHT_MAX_KG = 300.0

MUSCLE_GROUPS = [
    "Chest",
    "Back",
    "Shoulders",
    "Biceps",
    "Triceps",
    "Legs",
    "Core",
    "Cardio",
    "Full Body",
]

EXERCISE_CANONICAL_MAP = {
    "bench": "Bench Press",
    "bench press": "Bench Press",
    "benchpress": "Bench Press",
    "flat bench": "Bench Press",
    "flat bench press": "Bench Press",
    "bb bench": "Bench Press",
    "barbell bench": "Bench Press",
    "barbell bench press": "Bench Press",
    "incline bench": "Incline Bench Press",
    "incline bench press": "Incline Bench Press",
    "incline db press": "Incline Dumbbell Press",
    "incline dumbbell press": "Incline Dumbbell Press",
    "deadlift": "Deadlift",
    "dl": "Deadlift",
    "rdl": "Romanian Deadlift",
    "romanian deadlift": "Romanian Deadlift",
    "squat": "Squat",
    "back squat": "Squat",
    "front squat": "Front Squat",
    "ohp": "Overhead Press",
    "overhead press": "Overhead Press",
    "shoulder press": "Overhead Press",
    "military press": "Overhead Press",
    "pullup": "Pull Up",
    "pullups": "Pull Up",
    "pull up": "Pull Up",
    "pull ups": "Pull Up",
    "chinup": "Chin Up",
    "chin up": "Chin Up",
    "pushup": "Push Up",
    "push up": "Push Up",
    "lat pulldown": "Lat Pulldown",
    "lat pull down": "Lat Pulldown",
}

MEDAL_DEFINITIONS = [
    {
        "medal_key": "first_session",
        "medal_name": "First Rep",
        "medal_emoji": "\U0001F389",
        "description": "Logged first workout",
    },
    {
        "medal_key": "streak_7",
        "medal_name": "Week Warrior",
        "medal_emoji": "\U0001F525",
        "description": "7 day streak",
    },
    {
        "medal_key": "streak_30",
        "medal_name": "Iron Monk",
        "medal_emoji": "\U0001F30B",
        "description": "30 day streak",
    },
    {
        "medal_key": "total_sessions_10",
        "medal_name": "Getting Serious",
        "medal_emoji": "\U0001F4AA",
        "description": "10 total sessions",
    },
    {
        "medal_key": "total_sessions_50",
        "medal_name": "Dedicated Beast",
        "medal_emoji": "\U0001F9BE",
        "description": "50 total sessions",
    },
    {
        "medal_key": "bench_100",
        "medal_name": "Century Club",
        "medal_emoji": "\U0001F3CB\uFE0F",
        "description": "Bench Press 100kg",
    },
    {
        "medal_key": "deadlift_100",
        "medal_name": "Triple Digits",
        "medal_emoji": "\u26A1",
        "description": "Deadlift 100kg",
    },
    {
        "medal_key": "squat_100",
        "medal_name": "King of the Rack",
        "medal_emoji": "\U0001F451",
        "description": "Squat 100kg",
    },
    {
        "medal_key": "volume_10000_session",
        "medal_name": "Volume Monster",
        "medal_emoji": "\U0001F4A5",
        "description": "10,000 kg in a single session",
    },
    {
        "medal_key": "pr_5_exercises",
        "medal_name": "PR Machine",
        "medal_emoji": "\U0001F3AF",
        "description": "PRs on 5 different exercises",
    },
    {
        "medal_key": "leg_day_avoider",
        "medal_name": "Leg Day? Never Heard of It",
        "medal_emoji": "\U0001F605",
        "description": "10 sessions with zero leg training",
    },
    {
        "medal_key": "leg_day_redeemed",
        "medal_name": "Legs Unlocked",
        "medal_emoji": "\U0001F9B5",
        "description": "Logged legs after being a leg day avoider",
    },
    {
        "medal_key": "all_muscle_groups",
        "medal_name": "Complete Package",
        "medal_emoji": "\U0001F31F",
        "description": "Trained every muscle group at least once",
    },
]


class SupabaseConfigError(RuntimeError):
    pass


def _ensure_config() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SupabaseConfigError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.")


def _headers(return_representation: bool = False) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if return_representation:
        headers["Prefer"] = "return=representation"
    return headers


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: Any | None = None,
    return_representation: bool = False,
) -> Any:
    _ensure_config()
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            url,
            headers=_headers(return_representation=return_representation),
            params=params,
            json=payload,
        )

    if response.status_code >= 400:
        logger.error("Supabase error %s: %s", response.status_code, response.text)
        raise RuntimeError(f"Supabase request failed: {response.status_code}")

    if not response.text:
        return None

    try:
        return response.json()
    except ValueError:
        return None


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    cleaned = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_date_value(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_exercise_name(name: str) -> str:
    cleaned = " ".join(str(name).strip().split())
    if not cleaned:
        return ""

    normalized_key = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
    canonical = EXERCISE_CANONICAL_MAP.get(normalized_key)
    if canonical:
        return canonical

    return " ".join(word.capitalize() for word in cleaned.split())


def _calc_volume(weight_kg: float | None, reps: int | None, sets_count: int | None) -> float:
    if weight_kg is None or reps is None or sets_count is None:
        return 0.0
    return round(weight_kg * reps * sets_count, 2)


def _session_dates_from_rows(sessions: list[dict[str, Any]]) -> list[datetime.date]:
    unique_dates = {_parse_dt(item.get("logged_at")).date() for item in sessions}
    return sorted(unique_dates)


def _compute_streaks(sessions: list[dict[str, Any]]) -> tuple[int, int]:
    if not sessions:
        return 0, 0

    dates = _session_dates_from_rows(sessions)
    if not dates:
        return 0, 0

    longest_streak = 1
    current_run = 1
    for index in range(1, len(dates)):
        if (dates[index] - dates[index - 1]).days == 1:
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 1

    latest = dates[-1]
    today = datetime.now(timezone.utc).date()
    current_streak = 0
    if (today - latest).days <= 1:
        current_streak = 1
        cursor = latest
        while True:
            previous = cursor - timedelta(days=1)
            if previous in dates:
                current_streak += 1
                cursor = previous
                continue
            break

    return current_streak, longest_streak


def _dashboard_url(token: str) -> str:
    return f"{FRONTEND_URL.rstrip('/')}/dashboard/{token}"


def _sanitize_phone_number(phone_number: str) -> str:
    # Canonical storage format is digits-only to avoid duplicate user rows
    # from +country-code vs no-plus variants.
    return "".join(char for char in str(phone_number) if char.isdigit())


async def get_or_create_user_silent(phone_number: str, name: str | None = None) -> tuple[dict[str, Any], bool]:
    normalized_phone = _sanitize_phone_number(phone_number)
    if not normalized_phone:
        raise ValueError("A valid phone number is required.")

    existing = await _request(
        "GET",
        "users",
        params={"phone_number": f"eq.{normalized_phone}", "select": "*", "limit": 1},
    )

    if existing:
        user = existing[0]
        desired_name = name.strip()[:80] if name else ""
        if desired_name and desired_name != str(user.get("name") or ""):
            updated_rows = await _request(
                "PATCH",
                "users",
                params={"id": f"eq.{user['id']}"},
                payload={"name": desired_name},
                return_representation=True,
            )
            if updated_rows:
                user = updated_rows[0]
        return user, False

    payload: dict[str, Any] = {"phone_number": normalized_phone}
    if name:
        payload["name"] = name.strip()[:80]
    created = await _request(
        "POST",
        "users",
        payload=payload,
        return_representation=True,
    )
    return created[0], True


async def get_or_create_user(phone_number: str, name: str | None = None) -> tuple[dict[str, Any], bool]:
    user, is_new = await get_or_create_user_silent(phone_number, name=name)
    if not is_new:
        return user, False

    welcome_message = (
        "Welcome to GymPulse! \U0001F4AA Just text me your workout like you'd tell a friend. "
        "Example: 'chest day - bench 80kg 4x8, incline DB 22.5kg 3x10'. "
        f"Here's your personal dashboard: {_dashboard_url(user['dashboard_token'])}. Bookmark it!\n\n"
        "Flexible formats work too, like: 'i did 30kg bench press' or 'bench 30kg x12, 35kg x10, 40kg x8'.\n\n"
        "Quick commands:\n"
        "- dashboard\n"
        "- stats\n"
        "- story\n"
        "- medals\n"
        "- weight 78.4kg"
    )

    try:
        await send_text(phone_number, welcome_message)
    except Exception:
        logger.exception("Failed to send welcome message to %s", phone_number)

    return user, is_new


def _normalize_body_weight(weight_kg: float | None) -> float | None:
    if weight_kg is None:
        return None
    rounded = round(float(weight_kg), 1)
    if rounded < BODY_WEIGHT_MIN_KG or rounded > BODY_WEIGHT_MAX_KG:
        return None
    return rounded


async def get_body_weight_logs(user_id: str, days: int = 180) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "user_id": f"eq.{user_id}",
        "select": "id,user_id,weight_kg,logged_on,source,created_at",
        "order": "logged_on.asc",
    }
    if days > 0:
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
        params["logged_on"] = f"gte.{cutoff}"
    rows = await _safe_request("GET", "body_weight_logs", params=params)
    if not isinstance(rows, list):
        return []
    return rows


def _body_weight_summary(weight_logs: list[dict[str, Any]]) -> dict[str, Any]:
    normalized: list[tuple[date, float]] = []
    for row in weight_logs:
        logged_on = _parse_date_value(row.get("logged_on"))
        weight_kg = _normalize_body_weight(_to_float(row.get("weight_kg")))
        if logged_on and weight_kg is not None:
            normalized.append((logged_on, weight_kg))

    normalized.sort(key=lambda item: item[0])

    series = [{"date": item[0].isoformat(), "weight_kg": item[1]} for item in normalized]
    latest_weight = series[-1]["weight_kg"] if series else None
    latest_date = normalized[-1][0] if normalized else None

    delta_last = None
    if len(normalized) >= 2:
        delta_last = round(normalized[-1][1] - normalized[-2][1], 2)

    delta_7d = None
    if latest_date:
        target = latest_date - timedelta(days=7)
        prior_candidates = [item for item in normalized if item[0] <= target]
        if prior_candidates:
            delta_7d = round(normalized[-1][1] - prior_candidates[-1][1], 2)

    today = datetime.now(timezone.utc).date()
    start_30 = today - timedelta(days=29)
    entries_30 = [item for item in normalized if item[0] >= start_30]
    adherence_30d = round((len(entries_30) / 30) * 100, 1) if entries_30 else 0.0

    start_7 = today - timedelta(days=6)
    last_7_values = [item[1] for item in normalized if item[0] >= start_7]
    avg_7d = round(sum(last_7_values) / len(last_7_values), 2) if last_7_values else None

    trend = "stable"
    if delta_last is not None:
        if delta_last > 0:
            trend = "up"
        elif delta_last < 0:
            trend = "down"

    return {
        "series": series,
        "latest_weight_kg": latest_weight,
        "latest_logged_on": latest_date.isoformat() if latest_date else None,
        "delta_vs_last_log_kg": delta_last,
        "delta_7d_kg": delta_7d,
        "avg_7d_kg": avg_7d,
        "logs_30d": len(entries_30),
        "adherence_30d_pct": adherence_30d,
        "trend": trend,
    }


async def save_body_weight_log(
    user_id: str,
    weight_kg: float,
    *,
    logged_on: date | None = None,
    source: str = "whatsapp",
) -> dict[str, Any]:
    normalized_weight = _normalize_body_weight(_to_float(weight_kg))
    if normalized_weight is None:
        raise ValueError("Weight must be between 25kg and 300kg.")

    target_date = logged_on or datetime.now(timezone.utc).date()
    target_iso = target_date.isoformat()

    existing = await _request(
        "GET",
        "body_weight_logs",
        params={
            "user_id": f"eq.{user_id}",
            "logged_on": f"eq.{target_iso}",
            "select": "id,user_id,weight_kg,logged_on,source,created_at",
            "limit": 1,
        },
    )

    saved_row: dict[str, Any]
    if existing:
        patched = await _request(
            "PATCH",
            "body_weight_logs",
            params={"id": f"eq.{existing[0]['id']}"},
            payload={"weight_kg": normalized_weight, "source": source},
            return_representation=True,
        )
        saved_row = patched[0] if patched else existing[0]
    else:
        inserted = await _request(
            "POST",
            "body_weight_logs",
            payload={
                "user_id": user_id,
                "weight_kg": normalized_weight,
                "logged_on": target_iso,
                "source": source,
            },
            return_representation=True,
        )
        saved_row = inserted[0]

    logs = await get_body_weight_logs(user_id, days=180)
    return {"entry": saved_row, "summary": _body_weight_summary(logs)}


async def has_body_weight_log_for_date(user_id: str, target_date: date | None = None) -> bool:
    on_date = target_date or datetime.now(timezone.utc).date()
    try:
        rows = await _request(
            "GET",
            "body_weight_logs",
            params={
                "user_id": f"eq.{user_id}",
                "logged_on": f"eq.{on_date.isoformat()}",
                "select": "id",
                "limit": 1,
            },
        )
        return bool(rows)
    except Exception:
        logger.exception("Unable to read body weight logs for user %s", user_id)
        return False


async def should_prompt_for_weight(user: dict[str, Any]) -> bool:
    user_id = str(user.get("id") or "")
    if not user_id:
        return False
    if "last_weight_prompted_at" not in user:
        # Schema is likely not migrated yet; do not spam prompts.
        return False

    if await has_body_weight_log_for_date(user_id):
        return False

    last_prompted = _parse_date_value(user.get("last_weight_prompted_at"))
    today = datetime.now(timezone.utc).date()
    return last_prompted != today


async def mark_weight_prompted_today(user_id: str) -> None:
    today_iso = datetime.now(timezone.utc).date().isoformat()
    await _safe_request(
        "PATCH",
        "users",
        params={"id": f"eq.{user_id}"},
        payload={"last_weight_prompted_at": today_iso},
    )


async def save_session(user_id: str, raw_message: str, exercises: list[dict[str, Any]]) -> dict[str, Any]:
    notes = [item.get("notes") for item in exercises if item.get("notes")]
    notes_text = "; ".join(dict.fromkeys(str(note).strip() for note in notes if str(note).strip()))

    session_rows = await _request(
        "POST",
        "sessions",
        payload={
            "user_id": user_id,
            "raw_message": raw_message,
            "notes": notes_text or None,
        },
        return_representation=True,
    )
    session = session_rows[0]

    rows_to_insert: list[dict[str, Any]] = []
    total_volume = 0.0

    for exercise in exercises:
        name = _normalize_exercise_name(str(exercise.get("exercise_name", "")))
        muscle_group = str(exercise.get("muscle_group", "Full Body")).strip() or "Full Body"
        if muscle_group not in MUSCLE_GROUPS:
            muscle_group = "Full Body"

        weight_kg = _to_float(exercise.get("weight_kg"))
        reps = _to_int(exercise.get("reps"))
        sets_count = _to_int(exercise.get("sets_count"))

        total_volume += _calc_volume(weight_kg, reps, sets_count)
        rows_to_insert.append(
            {
                "session_id": session["id"],
                "user_id": user_id,
                "exercise_name": name,
                "muscle_group": muscle_group,
                "weight_kg": weight_kg,
                "reps": reps,
                "sets_count": sets_count,
                "logged_at": session.get("logged_at"),
            }
        )

    if rows_to_insert:
        await _request("POST", "sets", payload=rows_to_insert)

    return {
        "session": session,
        "exercises_saved": len(rows_to_insert),
        "total_volume": round(total_volume, 2),
    }


async def update_personal_records(user_id: str, exercises: list[dict[str, Any]]) -> list[dict[str, Any]]:
    new_prs: list[dict[str, Any]] = []

    for exercise in exercises:
        weight_kg = _to_float(exercise.get("weight_kg"))
        if weight_kg is None:
            continue

        exercise_name = _normalize_exercise_name(str(exercise.get("exercise_name", "")))
        if not exercise_name:
            continue

        existing = await _request(
            "GET",
            "personal_records",
            params={
                "user_id": f"eq.{user_id}",
                "exercise_name": f"eq.{exercise_name}",
                "select": "*",
                "limit": 1,
            },
        )

        if not existing:
            await _request(
                "POST",
                "personal_records",
                payload={
                    "user_id": user_id,
                    "exercise_name": exercise_name,
                    "weight_kg": weight_kg,
                },
            )
            new_prs.append({"exercise_name": exercise_name, "weight_kg": weight_kg})
            continue

        current_weight = _to_float(existing[0].get("weight_kg")) or 0.0
        if weight_kg > current_weight:
            await _request(
                "PATCH",
                "personal_records",
                params={"id": f"eq.{existing[0]['id']}"},
                payload={"weight_kg": weight_kg, "achieved_at": datetime.now(timezone.utc).isoformat()},
                return_representation=True,
            )
            new_prs.append({"exercise_name": exercise_name, "weight_kg": weight_kg})

    return new_prs


def _max_lift_for_keyword(sets_rows: list[dict[str, Any]], keyword: str) -> float:
    matches = []
    for row in sets_rows:
        exercise_name = str(row.get("exercise_name", "")).lower()
        if keyword in exercise_name:
            weight = _to_float(row.get("weight_kg"))
            if weight is not None:
                matches.append(weight)
    return max(matches) if matches else 0.0


def _session_volume_map(sets_rows: list[dict[str, Any]]) -> dict[str, float]:
    volumes: dict[str, float] = defaultdict(float)
    for row in sets_rows:
        session_id = str(row.get("session_id"))
        if not session_id:
            continue
        row_volume = _to_float(row.get("total_volume_kg"))
        if row_volume is None:
            row_volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))
        volumes[session_id] += row_volume
    return {key: round(value, 2) for key, value in volumes.items()}


async def check_and_award_medals(user_id: str) -> list[dict[str, Any]]:
    earned_rows = await _request(
        "GET",
        "medals",
        params={"user_id": f"eq.{user_id}", "select": "*"},
    )
    earned_keys = {row.get("medal_key") for row in earned_rows}

    sessions = await _request(
        "GET",
        "sessions",
        params={"user_id": f"eq.{user_id}", "select": "id,logged_at", "order": "logged_at.asc"},
    )
    sets_rows = await _request(
        "GET",
        "sets",
        params={
            "user_id": f"eq.{user_id}",
            "select": "session_id,exercise_name,muscle_group,weight_kg,reps,sets_count,total_volume_kg,logged_at",
        },
    )
    prs = await _request(
        "GET",
        "personal_records",
        params={"user_id": f"eq.{user_id}", "select": "exercise_name"},
    )

    total_sessions = len(sessions)
    current_streak, _ = _compute_streaks(sessions)

    session_volume_lookup = _session_volume_map(sets_rows)
    max_session_volume = max(session_volume_lookup.values()) if session_volume_lookup else 0.0

    leg_sessions = {row.get("session_id") for row in sets_rows if str(row.get("muscle_group")) == "Legs"}
    has_leg_training = bool(leg_sessions)

    trained_groups = {
        str(row.get("muscle_group"))
        for row in sets_rows
        if str(row.get("muscle_group", "")).strip() in MUSCLE_GROUPS
    }

    conditions = {
        "first_session": total_sessions >= 1,
        "streak_7": current_streak >= 7,
        "streak_30": current_streak >= 30,
        "total_sessions_10": total_sessions >= 10,
        "total_sessions_50": total_sessions >= 50,
        "bench_100": _max_lift_for_keyword(sets_rows, "bench") >= 100,
        "deadlift_100": _max_lift_for_keyword(sets_rows, "deadlift") >= 100,
        "squat_100": _max_lift_for_keyword(sets_rows, "squat") >= 100,
        "volume_10000_session": max_session_volume >= 10000,
        "pr_5_exercises": len(prs) >= 5,
        "leg_day_avoider": total_sessions >= 10 and not has_leg_training,
        "leg_day_redeemed": "leg_day_avoider" in earned_keys and has_leg_training,
        "all_muscle_groups": all(group in trained_groups for group in MUSCLE_GROUPS),
    }

    newly_awarded: list[dict[str, Any]] = []

    for medal in MEDAL_DEFINITIONS:
        key = medal["medal_key"]
        if key in earned_keys:
            continue
        if not conditions.get(key, False):
            continue

        inserted = await _request(
            "POST",
            "medals",
            payload={"user_id": user_id, **medal},
            return_representation=True,
        )
        if inserted:
            newly_awarded.append(inserted[0])
            earned_keys.add(key)

    return newly_awarded


async def get_user_by_token(token: str) -> dict[str, Any] | None:
    rows = await _request(
        "GET",
        "users",
        params={"dashboard_token": f"eq.{token}", "select": "*", "limit": 1},
    )
    if not rows:
        return None
    return rows[0]


async def get_user_by_phone(phone_number: str) -> dict[str, Any] | None:
    normalized_phone = _sanitize_phone_number(phone_number)
    if not normalized_phone:
        return None

    rows = await _request(
        "GET",
        "users",
        params={"phone_number": f"eq.{normalized_phone}", "select": "*", "limit": 1},
    )
    if not rows:
        return None
    return rows[0]


async def _get_sessions_and_sets(user_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sessions = await _request(
        "GET",
        "sessions",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,logged_at,raw_message,notes",
            "order": "logged_at.desc",
        },
    )
    sets_rows = await _request(
        "GET",
        "sets",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,session_id,user_id,exercise_name,muscle_group,weight_kg,reps,sets_count,total_volume_kg,logged_at",
            "order": "logged_at.asc",
        },
    )
    return sessions, sets_rows


def _weekly_volume(sets_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weekly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for row in sets_rows:
        logged_at = _parse_dt(row.get("logged_at"))
        week_start = (logged_at.date() - timedelta(days=logged_at.weekday())).isoformat()
        group = str(row.get("muscle_group") or "Full Body")
        if group not in MUSCLE_GROUPS:
            group = "Full Body"

        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))

        weekly[week_start][group] += volume

    rows: list[dict[str, Any]] = []
    for week_start in sorted(weekly.keys()):
        entry = {"week_start": week_start}
        total = 0.0
        for group in MUSCLE_GROUPS:
            value = round(weekly[week_start].get(group, 0.0), 2)
            entry[group] = value
            total += value
        entry["total"] = round(total, 2)
        rows.append(entry)

    return rows


def _progress_data(sets_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    # Daily progression per exercise. We track max load and same-day volume.
    progress: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"max_weight": 0.0, "volume_kg": 0.0}))

    for row in sets_rows:
        weight = _to_float(row.get("weight_kg"))
        if weight is None:
            continue

        exercise = _normalize_exercise_name(str(row.get("exercise_name", "")))
        if not exercise:
            continue

        day = _parse_dt(row.get("logged_at")).date().isoformat()
        set_volume = _to_float(row.get("total_volume_kg"))
        if set_volume is None:
            set_volume = _calc_volume(weight, _to_int(row.get("reps")), _to_int(row.get("sets_count")))

        bucket = progress[exercise][day]
        bucket["max_weight"] = max(bucket.get("max_weight", 0.0), weight)
        bucket["volume_kg"] = round(bucket.get("volume_kg", 0.0) + max(set_volume, 0.0), 2)

    output: dict[str, list[dict[str, Any]]] = {}
    for exercise, day_map in progress.items():
        points = [
            {
                "date": day,
                "max_weight": round(values.get("max_weight", 0.0), 2),
                "volume_kg": round(values.get("volume_kg", 0.0), 2),
            }
            for day, values in sorted(day_map.items())
        ]
        output[exercise] = points

    return output


def _radar_distribution(sets_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    totals: dict[str, float] = {group: 0.0 for group in MUSCLE_GROUPS}

    for row in sets_rows:
        if _parse_dt(row.get("logged_at")) < cutoff:
            continue

        group = str(row.get("muscle_group") or "Full Body")
        if group not in MUSCLE_GROUPS:
            group = "Full Body"

        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))
        totals[group] += volume

    return [{"muscle_group": group, "volume": round(value, 2)} for group, value in totals.items()]


def _heatmap_data(sets_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=183)
    per_day: dict[str, float] = defaultdict(float)

    for row in sets_rows:
        day = _parse_dt(row.get("logged_at")).date().isoformat()
        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))
        per_day[day] += volume

    rows: list[dict[str, Any]] = []
    cursor = start
    while cursor <= today:
        key = cursor.isoformat()
        volume = round(per_day.get(key, 0.0), 2)
        if volume == 0:
            intensity = 0
        elif volume < 2000:
            intensity = 1
        elif volume < 5000:
            intensity = 2
        else:
            intensity = 3

        rows.append({"date": key, "volume": volume, "intensity": intensity})
        cursor += timedelta(days=1)

    return rows


def _recent_sessions(
    sessions: list[dict[str, Any]],
    sets_rows: list[dict[str, Any]],
    session_volume_lookup: dict[str, float],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sets_rows:
        grouped[str(row.get("session_id"))].append(row)

    output: list[dict[str, Any]] = []
    for session in sessions[:10]:
        session_id = str(session.get("id"))
        rows = grouped.get(session_id, [])

        exercises = []
        muscle_groups = set()
        for row in rows:
            muscle = str(row.get("muscle_group") or "Full Body")
            muscle_groups.add(muscle)
            exercises.append(
                {
                    "exercise_name": _normalize_exercise_name(str(row.get("exercise_name", ""))),
                    "muscle_group": muscle,
                    "weight_kg": _to_float(row.get("weight_kg")),
                    "reps": _to_int(row.get("reps")),
                    "sets_count": _to_int(row.get("sets_count")),
                    "total_volume_kg": _to_float(row.get("total_volume_kg")),
                }
            )

        output.append(
            {
                "id": session_id,
                "logged_at": session.get("logged_at"),
                "raw_message": session.get("raw_message"),
                "notes": session.get("notes"),
                "muscle_groups": sorted(muscle_groups),
                "total_volume": round(session_volume_lookup.get(session_id, 0.0), 2),
                "exercises": exercises,
            }
        )

    return output


def _quick_week_stats(sessions: list[dict[str, Any]], sets_rows: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    week_start = now.date() - timedelta(days=now.date().weekday())

    sessions_in_week = [session for session in sessions if _parse_dt(session.get("logged_at")).date() >= week_start]
    week_session_ids = {session.get("id") for session in sessions_in_week}

    week_sets = [row for row in sets_rows if row.get("session_id") in week_session_ids]

    total_volume = 0.0
    day_volume: dict[str, float] = defaultdict(float)
    muscle_volume: dict[str, float] = defaultdict(float)
    for row in week_sets:
        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))

        total_volume += volume
        day_key = _parse_dt(row.get("logged_at")).strftime("%A")
        day_volume[day_key] += volume

        group = str(row.get("muscle_group") or "Full Body")
        if group not in MUSCLE_GROUPS:
            group = "Full Body"
        muscle_volume[group] += volume

    strongest_day = max(day_volume.items(), key=lambda item: item[1])[0] if day_volume else "N/A"
    most_trained = max(muscle_volume.items(), key=lambda item: item[1])[0] if muscle_volume else "N/A"
    current_streak, longest_streak = _compute_streaks(sessions)

    return {
        "sessions": len(sessions_in_week),
        "total_volume": round(total_volume, 2),
        "strongest_day": strongest_day,
        "most_trained": most_trained,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }


def _percent_change(current_value: float, previous_value: float) -> float | None:
    if previous_value <= 0:
        return None
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def _balance_score(radar_30d: list[dict[str, Any]]) -> int:
    volumes = [max(_to_float(item.get("volume")) or 0.0, 0.0) for item in radar_30d]
    total = sum(volumes)
    if total <= 0:
        return 0

    shares = [value / total for value in volumes if value > 0]
    if not shares:
        return 0

    hhi = sum(share * share for share in shares)
    n = len(MUSCLE_GROUPS)
    min_hhi = 1 / n
    normalized = 1 - ((hhi - min_hhi) / max(1 - min_hhi, 1e-9))
    return max(0, min(100, int(round(normalized * 100))))


def _progression_stats(progress: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tracked = 0
    improving = 0
    best_delta = 0.0
    best_exercise = None

    for exercise_name, points in progress.items():
        if len(points) < 2:
            continue

        latest = _to_float(points[-1].get("max_weight")) or 0.0
        previous = _to_float(points[-2].get("max_weight")) or 0.0
        delta = round(latest - previous, 2)

        tracked += 1
        if delta > 0:
            improving += 1
        if delta > best_delta:
            best_delta = delta
            best_exercise = exercise_name

    score = int(round((improving / tracked) * 100)) if tracked > 0 else 0
    return {
        "tracked_exercises": tracked,
        "improving_exercises": improving,
        "score": score,
        "best_exercise": best_exercise,
        "best_delta_kg": round(best_delta, 2) if best_exercise else None,
    }


def _coach_recommendation(
    *,
    sessions_7d: int,
    progression_score: int,
    balance_score: int,
    leg_share_pct: float,
    body_weight_adherence_30d: float,
    undertrained_groups: list[str],
) -> str:
    if body_weight_adherence_30d < 40:
        return "Log bodyweight daily for better cut/bulk decision support."
    if sessions_7d < 3:
        return "Aim for at least 3 sessions this week to build momentum."
    if leg_share_pct < 15:
        return "Leg volume is low. Add one dedicated lower-body day this week."
    if progression_score < 35:
        return "Progression is stalling. Nudge key lifts by 1.25-2.5kg or add 1-2 reps."
    if balance_score < 45 and undertrained_groups:
        return f"Training is imbalanced. Add work for: {', '.join(undertrained_groups[:3])}."
    return "Solid week. Keep progressive overload steady and recovery consistent."


def _build_coach_insights(
    sessions: list[dict[str, Any]],
    weekly_volume: list[dict[str, Any]],
    radar_30d: list[dict[str, Any]],
    progress: dict[str, list[dict[str, Any]]],
    body_weight_summary: dict[str, Any],
) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    sessions_7d = sum(1 for session in sessions if _parse_dt(session.get("logged_at")).date() >= today - timedelta(days=6))
    sessions_28d = sum(
        1 for session in sessions if _parse_dt(session.get("logged_at")).date() >= today - timedelta(days=27)
    )

    current_streak, _ = _compute_streaks(sessions)
    consistency_score = min(100, int(round((sessions_28d / 16) * 70 + min(current_streak, 14) * 2.1)))

    progression = _progression_stats(progress)
    balance_score = _balance_score(radar_30d)

    weekly_totals = [max(_to_float(row.get("total")) or 0.0, 0.0) for row in weekly_volume[-4:]]
    weekly_trend = None
    if len(weekly_totals) >= 2:
        weekly_trend = _percent_change(weekly_totals[-1], weekly_totals[-2])

    totals_by_group = {str(item.get("muscle_group")): max(_to_float(item.get("volume")) or 0.0, 0.0) for item in radar_30d}
    total_30d_volume = sum(totals_by_group.values())
    radar_sorted = sorted(radar_30d, key=lambda item: _to_float(item.get("volume")) or 0.0, reverse=True)
    top_muscle_group = radar_sorted[0].get("muscle_group") if radar_sorted else "N/A"

    avg_group_volume = (total_30d_volume / len(MUSCLE_GROUPS)) if MUSCLE_GROUPS else 0.0
    undertrained_threshold = max(avg_group_volume * 0.6, 1.0)
    undertrained_groups = [
        group
        for group in sorted(
            MUSCLE_GROUPS,
            key=lambda group: (
                0 if totals_by_group.get(group, 0.0) <= 0 else 1,
                0 if group == "Legs" else 1,
                totals_by_group.get(group, 0.0),
            ),
        )
        if totals_by_group.get(group, 0.0) <= undertrained_threshold and group != top_muscle_group
    ]
    if not undertrained_groups:
        undertrained_groups = [
            group
            for group in sorted(
                MUSCLE_GROUPS,
                key=lambda group: (
                    0 if group == "Legs" else 1,
                    totals_by_group.get(group, 0.0),
                ),
            )
            if group != top_muscle_group
        ][:3]

    leg_share_pct = round(((totals_by_group.get("Legs", 0.0) / total_30d_volume) * 100), 1) if total_30d_volume > 0 else 0.0

    push_volume = totals_by_group.get("Chest", 0.0) + totals_by_group.get("Shoulders", 0.0) + totals_by_group.get("Triceps", 0.0)
    pull_volume = totals_by_group.get("Back", 0.0) + totals_by_group.get("Biceps", 0.0)
    push_pull_ratio = round((push_volume / pull_volume), 2) if pull_volume > 0 else None

    body_weight_adherence_30d = float(body_weight_summary.get("adherence_30d_pct") or 0.0)
    recommendation = _coach_recommendation(
        sessions_7d=sessions_7d,
        progression_score=progression["score"],
        balance_score=balance_score,
        leg_share_pct=leg_share_pct,
        body_weight_adherence_30d=body_weight_adherence_30d,
        undertrained_groups=undertrained_groups,
    )

    return {
        "consistency_score": consistency_score,
        "progression_score": progression["score"],
        "balance_score": balance_score,
        "sessions_7d": sessions_7d,
        "sessions_28d": sessions_28d,
        "weekly_volume_trend_pct": weekly_trend,
        "top_muscle_group_30d": top_muscle_group,
        "undertrained_groups": undertrained_groups[:6],
        "tracked_exercises": progression["tracked_exercises"],
        "improving_exercises": progression["improving_exercises"],
        "best_progression_exercise": progression["best_exercise"],
        "best_progression_delta_kg": progression["best_delta_kg"],
        "leg_share_pct_30d": leg_share_pct,
        "push_pull_ratio_30d": push_pull_ratio,
        "body_weight_adherence_30d_pct": body_weight_adherence_30d,
        "recommendation": recommendation,
    }


async def get_user_stats(user_id: str) -> dict[str, Any]:
    sessions, sets_rows = await _get_sessions_and_sets(user_id)
    body_weight_logs = await get_body_weight_logs(user_id, days=180)
    body_weight_summary = _body_weight_summary(body_weight_logs)

    prs = await _request(
        "GET",
        "personal_records",
        params={"user_id": f"eq.{user_id}", "select": "exercise_name,weight_kg,achieved_at"},
    )
    medals = await _request(
        "GET",
        "medals",
        params={"user_id": f"eq.{user_id}", "select": "*"},
    )

    session_volume_lookup = _session_volume_map(sets_rows)
    total_volume = round(sum(session_volume_lookup.values()), 2)
    current_streak, longest_streak = _compute_streaks(sessions)
    progress = _progress_data(sets_rows)
    weekly_volume = _weekly_volume(sets_rows)
    radar_30d = _radar_distribution(sets_rows)
    quick_stats = _quick_week_stats(sessions, sets_rows)
    quick_stats["latest_weight_kg"] = body_weight_summary.get("latest_weight_kg")
    quick_stats["weight_delta_7d_kg"] = body_weight_summary.get("delta_7d_kg")
    quick_stats["weight_logs_30d"] = body_weight_summary.get("logs_30d")

    top_muscle_map: dict[str, float] = defaultdict(float)
    for row in sets_rows:
        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))
        group = str(row.get("muscle_group") or "Full Body")
        if group not in MUSCLE_GROUPS:
            group = "Full Body"
        top_muscle_map[group] += volume

    top_muscle_group = max(top_muscle_map.items(), key=lambda item: item[1])[0] if top_muscle_map else "N/A"

    return {
        "summary": {
            "total_sessions": len(sessions),
            "total_volume_kg": total_volume,
            "total_volume_tonnes": round(total_volume / 1000, 2),
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "top_muscle_group": top_muscle_group,
            "latest_weight_kg": body_weight_summary.get("latest_weight_kg"),
        },
        "progress": progress,
        "weekly_volume": weekly_volume,
        "radar_30d": radar_30d,
        "heatmap": _heatmap_data(sets_rows),
        "recent_sessions": _recent_sessions(sessions, sets_rows, session_volume_lookup),
        "personal_records": prs,
        "medals": medals,
        "quick_stats": quick_stats,
        "body_weight": body_weight_summary,
        "coach_insights": _build_coach_insights(
            sessions=sessions,
            weekly_volume=weekly_volume,
            radar_30d=radar_30d,
            progress=progress,
            body_weight_summary=body_weight_summary,
        ),
    }


async def get_exercise_history(user_id: str) -> dict[str, Any]:
    sets_rows = await _request(
        "GET",
        "sets",
        params={
            "user_id": f"eq.{user_id}",
            "select": "id,exercise_name,muscle_group,weight_kg,reps,sets_count,total_volume_kg,logged_at,session_id",
            "order": "logged_at.desc",
        },
    )

    history = []
    for row in sets_rows:
        history.append(
            {
                "id": row.get("id"),
                "exercise_name": _normalize_exercise_name(str(row.get("exercise_name", ""))),
                "muscle_group": row.get("muscle_group"),
                "weight_kg": _to_float(row.get("weight_kg")),
                "reps": _to_int(row.get("reps")),
                "sets_count": _to_int(row.get("sets_count")),
                "total_volume_kg": _to_float(row.get("total_volume_kg")),
                "logged_at": row.get("logged_at"),
                "session_id": row.get("session_id"),
            }
        )

    return {"history": history}


async def get_medals_for_user(user_id: str) -> dict[str, Any]:
    earned_rows = await _request(
        "GET",
        "medals",
        params={"user_id": f"eq.{user_id}", "select": "medal_key,medal_name,medal_emoji,description,awarded_at"},
    )
    by_key = {item.get("medal_key"): item for item in earned_rows}

    all_medals = []
    for medal in MEDAL_DEFINITIONS:
        earned = by_key.get(medal["medal_key"])
        all_medals.append(
            {
                **medal,
                "earned": bool(earned),
                "awarded_at": earned.get("awarded_at") if earned else None,
            }
        )

    return {
        "earned": earned_rows,
        "all_medals": all_medals,
        "total_earned": len(earned_rows),
        "total_available": len(MEDAL_DEFINITIONS),
    }


async def get_weekly_muscle_group_change(user_id: str, muscle_group: str) -> float | None:
    sessions, sets_rows = await _get_sessions_and_sets(user_id)
    if not sessions:
        return None

    now = datetime.now(timezone.utc)
    current_week_start = now.date() - timedelta(days=now.date().weekday())
    prev_week_start = current_week_start - timedelta(days=7)

    current_volume = 0.0
    previous_volume = 0.0
    for row in sets_rows:
        if str(row.get("muscle_group")) != muscle_group:
            continue

        row_date = _parse_dt(row.get("logged_at")).date()
        volume = _to_float(row.get("total_volume_kg"))
        if volume is None:
            volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))

        if row_date >= current_week_start:
            current_volume += volume
        elif prev_week_start <= row_date < current_week_start:
            previous_volume += volume

    if previous_volume <= 0:
        return None

    change = ((current_volume - previous_volume) / previous_volume) * 100
    return round(change, 1)


async def get_dashboard_link_for_user(user_id: str) -> str | None:
    rows = await _request(
        "GET",
        "users",
        params={"id": f"eq.{user_id}", "select": "dashboard_token", "limit": 1},
    )
    if not rows:
        return None
    return _dashboard_url(rows[0]["dashboard_token"])


async def get_dashboard_link_by_phone(phone_number: str) -> str | None:
    normalized_phone = _sanitize_phone_number(phone_number)
    if not normalized_phone:
        return None

    rows = await _request(
        "GET",
        "users",
        params={"phone_number": f"eq.{normalized_phone}", "select": "dashboard_token", "limit": 1},
    )
    if not rows:
        return None
    return _dashboard_url(rows[0]["dashboard_token"])


def _mask_phone_number(phone_number: str) -> str:
    digits = "".join(char for char in str(phone_number) if char.isdigit())
    if len(digits) < 6:
        return str(phone_number)
    if len(digits) <= 8:
        return f"{digits[:2]}***{digits[-2:]}"
    return f"+{digits[:2]} {digits[2:4]}*****{digits[-3:]}"


def _is_subscription_active(subscription: dict[str, Any] | None) -> bool:
    if not subscription:
        return False

    status = str(subscription.get("status", "")).strip().lower()
    if status not in PRO_ACTIVE_STATUSES:
        return False

    expires_at = subscription.get("expires_at")
    if not expires_at:
        return False

    return _parse_dt(expires_at) > datetime.now(timezone.utc)


def _latest_subscription_by_user(subscriptions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in sorted(subscriptions, key=lambda item: str(item.get("created_at") or "")):
        user_id = str(row.get("user_id") or "")
        if user_id:
            latest[user_id] = row
    return latest


def _date_range(days: int) -> list[datetime.date]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=max(days - 1, 0))
    return [start + timedelta(days=index) for index in range(days)]


def _date_key(dt_value: str | None) -> str | None:
    if not dt_value:
        return None
    return _parse_dt(dt_value).date().isoformat()


async def _safe_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: Any | None = None,
    return_representation: bool = False,
) -> Any:
    try:
        return await _request(
            method,
            path,
            params=params,
            payload=payload,
            return_representation=return_representation,
        )
    except Exception:
        logger.exception("Safe request failed for %s %s", method, path)
        return []


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    rows = await _request(
        "GET",
        "users",
        params={"id": f"eq.{user_id}", "select": "*", "limit": 1},
    )
    if not rows:
        return None
    return rows[0]


async def get_subscription_for_user(user_id: str) -> dict[str, Any] | None:
    rows = await _request(
        "GET",
        "subscriptions",
        params={
            "user_id": f"eq.{user_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": 1,
        },
    )
    if not rows:
        return None
    return rows[0]


async def upsert_subscription_for_user(
    user_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    existing = await get_subscription_for_user(user_id)
    if existing:
        patched = await _request(
            "PATCH",
            "subscriptions",
            params={"id": f"eq.{existing['id']}"},
            payload=updates,
            return_representation=True,
        )
        return patched[0] if patched else None

    payload = {"user_id": user_id, **updates}
    created = await _request(
        "POST",
        "subscriptions",
        payload=payload,
        return_representation=True,
    )
    return created[0] if created else None


async def get_subscription_by_razorpay(
    razorpay_subscription_id: str | None = None,
    razorpay_customer_id: str | None = None,
) -> dict[str, Any] | None:
    if razorpay_subscription_id:
        rows = await _request(
            "GET",
            "subscriptions",
            params={
                "razorpay_subscription_id": f"eq.{razorpay_subscription_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": 1,
            },
        )
        if rows:
            return rows[0]

    if razorpay_customer_id:
        rows = await _request(
            "GET",
            "subscriptions",
            params={
                "razorpay_customer_id": f"eq.{razorpay_customer_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": 1,
            },
        )
        if rows:
            return rows[0]

    return None


async def update_subscription_by_razorpay_ids(
    *,
    razorpay_subscription_id: str | None = None,
    razorpay_customer_id: str | None = None,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    existing = await get_subscription_by_razorpay(
        razorpay_subscription_id=razorpay_subscription_id,
        razorpay_customer_id=razorpay_customer_id,
    )
    if not existing:
        return None

    patched = await _request(
        "PATCH",
        "subscriptions",
        params={"id": f"eq.{existing['id']}"},
        payload=updates,
        return_representation=True,
    )
    return patched[0] if patched else None


async def is_user_pro(user_id: str) -> bool:
    subscription = await get_subscription_for_user(user_id)
    return _is_subscription_active(subscription)


async def log_payment_event(
    *,
    event_type: str,
    user_id: str | None,
    phone_number: str | None,
    status: str,
    amount_inr: float | None = None,
    razorpay_payment_id: str | None = None,
    razorpay_subscription_id: str | None = None,
    razorpay_customer_id: str | None = None,
    payload_json: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> None:
    await _safe_request(
        "POST",
        "payment_events",
        payload={
            "event_type": event_type,
            "user_id": user_id,
            "phone_number": phone_number,
            "status": status,
            "amount_inr": amount_inr,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_customer_id": razorpay_customer_id,
            "payload_json": payload_json,
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
        },
    )


async def _get_admin_base_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    users = await _request(
        "GET",
        "users",
        params={"select": "id,phone_number,name,created_at", "order": "created_at.asc"},
    )
    sessions = await _request(
        "GET",
        "sessions",
        params={"select": "id,user_id,logged_at", "order": "logged_at.asc"},
    )
    subscriptions = await _request(
        "GET",
        "subscriptions",
        params={
            "select": "id,user_id,status,plan,expires_at,started_at,created_at,razorpay_subscription_id,razorpay_customer_id",
            "order": "created_at.asc",
        },
    )
    return users, sessions, subscriptions


def _build_session_metrics(sessions: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, str]]:
    sessions_by_user: dict[str, int] = defaultdict(int)
    last_active_by_user: dict[str, str] = {}

    for row in sessions:
        user_id = str(row.get("user_id") or "")
        if not user_id:
            continue
        sessions_by_user[user_id] += 1
        logged_at = str(row.get("logged_at") or "")
        if logged_at and logged_at > str(last_active_by_user.get(user_id, "")):
            last_active_by_user[user_id] = logged_at

    return sessions_by_user, last_active_by_user


def _subscription_plan_status(subscription: dict[str, Any] | None) -> tuple[str, str]:
    if not subscription:
        return "free", "free"

    is_active = _is_subscription_active(subscription)
    if is_active:
        return "pro", "active"

    status = str(subscription.get("status") or "free").lower()
    if status == "active" and subscription.get("expires_at"):
        try:
            if _parse_dt(subscription.get("expires_at")) <= datetime.now(timezone.utc):
                return "pro", "expired"
        except Exception:
            pass
    if status in {"cancelled", "expired"}:
        return "pro", "expired"
    return "free", "free"


def _count_new_users(users: list[dict[str, Any]]) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    daily = 0
    weekly = 0
    monthly = 0
    for row in users:
        created = _parse_dt(row.get("created_at")).date()
        if created == today:
            daily += 1
        if created >= week_start:
            weekly += 1
        if created >= month_start:
            monthly += 1
    return {"today": daily, "week": weekly, "month": monthly}


async def get_admin_overview_data() -> dict[str, Any]:
    users, sessions, subscriptions = await _get_admin_base_rows()
    events = await _safe_request(
        "GET",
        "payment_events",
        params={
            "select": "event_type,amount_inr,status,occurred_at",
            "order": "occurred_at.asc",
        },
    )

    latest_subscriptions = _latest_subscription_by_user(subscriptions)
    sessions_by_user, _ = _build_session_metrics(sessions)

    total_registered_users = len(users)
    pro_user_ids = {
        user_id for user_id, subscription in latest_subscriptions.items() if _is_subscription_active(subscription)
    }
    total_pro_users = len(pro_user_ids)
    free_users = max(total_registered_users - total_pro_users, 0)

    now = datetime.now(timezone.utc)
    month_start = now.date().replace(day=1)
    churn_this_month = 0
    for event in events:
        if str(event.get("event_type")) != "subscription.cancelled":
            continue
        occurred = _parse_dt(event.get("occurred_at")).date()
        if occurred >= month_start:
            churn_this_month += 1

    signups_counts = {day.isoformat(): 0 for day in _date_range(30)}
    for user in users:
        day = _date_key(user.get("created_at"))
        if day in signups_counts:
            signups_counts[day] += 1

    successful_revenue_counts = {day.isoformat(): 0.0 for day in _date_range(30)}
    successful_events = [
        event for event in events if str(event.get("event_type")) in {"subscription.activated", "payment.captured"}
    ]
    for event in successful_events:
        day = _date_key(event.get("occurred_at"))
        if day not in successful_revenue_counts:
            continue
        amount = _to_float(event.get("amount_inr"))
        if amount is None:
            amount = float(PRO_MONTHLY_PRICE_INR)
        successful_revenue_counts[day] += amount

    dau_counts = {day.isoformat(): 0 for day in _date_range(30)}
    users_per_day: dict[str, set[str]] = defaultdict(set)
    for session in sessions:
        day = _date_key(session.get("logged_at"))
        user_id = str(session.get("user_id") or "")
        if day and user_id and day in dau_counts:
            users_per_day[day].add(user_id)
    for day, user_set in users_per_day.items():
        dau_counts[day] = len(user_set)

    new_users = _count_new_users(users)

    if successful_events:
        total_revenue_all_time = round(
            sum(_to_float(event.get("amount_inr")) or float(PRO_MONTHLY_PRICE_INR) for event in successful_events),
            2,
        )
    else:
        # Fallback if webhook events are not yet configured.
        estimated_paid_subscriptions = sum(
            1 for row in subscriptions if str(row.get("plan") or "").lower() not in {"", "free"}
        )
        total_revenue_all_time = float(estimated_paid_subscriptions * PRO_MONTHLY_PRICE_INR)

    total_revenue_month = float(total_pro_users * PRO_MONTHLY_PRICE_INR)

    return {
        "cards": {
            "total_registered_users": total_registered_users,
            "total_pro_users": total_pro_users,
            "free_users": free_users,
            "total_revenue_month": total_revenue_month,
            "total_revenue_all_time": total_revenue_all_time,
            "churn_this_month": churn_this_month,
            "new_users_today": new_users["today"],
            "new_users_week": new_users["week"],
            "new_users_month": new_users["month"],
            "daily_active_users_today": dau_counts.get(datetime.now(timezone.utc).date().isoformat(), 0),
            "tracked_users": len(sessions_by_user),
        },
        "signups_30d": [{"date": day, "count": signups_counts[day]} for day in sorted(signups_counts.keys())],
        "revenue_30d": [{"date": day, "amount": round(successful_revenue_counts[day], 2)} for day in sorted(successful_revenue_counts.keys())],
        "daily_active_users_30d": [{"date": day, "count": dau_counts[day]} for day in sorted(dau_counts.keys())],
    }


async def get_admin_users_data(
    *,
    search: str = "",
    plan_filter: str = "all",
    sort_by: str = "joined",
) -> dict[str, Any]:
    users, sessions, subscriptions = await _get_admin_base_rows()
    latest_subscriptions = _latest_subscription_by_user(subscriptions)
    sessions_by_user, last_active_by_user = _build_session_metrics(sessions)

    query = search.strip().lower()
    filtered_rows: list[dict[str, Any]] = []
    for user in users:
        phone_number = str(user.get("phone_number") or "")
        if query and query not in phone_number.lower():
            continue

        subscription = latest_subscriptions.get(user["id"])
        plan, status = _subscription_plan_status(subscription)
        if plan_filter == "pro" and plan != "pro":
            continue
        if plan_filter == "free" and plan != "free":
            continue
        if plan_filter == "expired" and status != "expired":
            continue

        filtered_rows.append(
            {
                "id": user["id"],
                "phone_number": phone_number,
                "masked_phone": _mask_phone_number(phone_number),
                "name": user.get("name"),
                "joined_at": user.get("created_at"),
                "plan": plan,
                "status": status,
                "expires_at": subscription.get("expires_at") if subscription else None,
                "sessions_count": sessions_by_user.get(user["id"], 0),
                "last_active": last_active_by_user.get(user["id"]),
            }
        )

    if sort_by == "sessions":
        filtered_rows.sort(key=lambda item: int(item.get("sessions_count") or 0), reverse=True)
    elif sort_by == "last_active":
        filtered_rows.sort(key=lambda item: str(item.get("last_active") or ""), reverse=True)
    else:
        filtered_rows.sort(key=lambda item: str(item.get("joined_at") or ""), reverse=True)

    return {
        "users": filtered_rows,
        "count": len(filtered_rows),
    }


def _all_sessions_payload(
    sessions: list[dict[str, Any]],
    sets_rows: list[dict[str, Any]],
    session_volume_lookup: dict[str, float],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sets_rows:
        grouped[str(row.get("session_id"))].append(row)

    output: list[dict[str, Any]] = []
    for session in sessions:
        session_id = str(session.get("id"))
        rows = grouped.get(session_id, [])

        exercises = []
        muscle_groups = set()
        for row in rows:
            muscle = str(row.get("muscle_group") or "Full Body")
            muscle_groups.add(muscle)
            exercises.append(
                {
                    "exercise_name": _normalize_exercise_name(str(row.get("exercise_name", ""))),
                    "muscle_group": muscle,
                    "weight_kg": _to_float(row.get("weight_kg")),
                    "reps": _to_int(row.get("reps")),
                    "sets_count": _to_int(row.get("sets_count")),
                    "total_volume_kg": _to_float(row.get("total_volume_kg")),
                }
            )

        output.append(
            {
                "id": session_id,
                "logged_at": session.get("logged_at"),
                "raw_message": session.get("raw_message"),
                "notes": session.get("notes"),
                "muscle_groups": sorted(muscle_groups),
                "total_volume": round(session_volume_lookup.get(session_id, 0.0), 2),
                "exercises": exercises,
            }
        )
    return output


async def get_admin_user_detail(user_id: str) -> dict[str, Any] | None:
    user = await get_user_by_id(user_id)
    if not user:
        return None

    sessions, sets_rows = await _get_sessions_and_sets(user_id)
    medals = await get_medals_for_user(user_id)
    stats = await get_user_stats(user_id)
    session_volume_lookup = _session_volume_map(sets_rows)

    return {
        "user": {
            "id": user["id"],
            "phone_number": user.get("phone_number"),
            "name": user.get("name"),
            "dashboard_token": user.get("dashboard_token"),
            "created_at": user.get("created_at"),
        },
        "stats": stats,
        "medals": medals,
        "all_sessions": _all_sessions_payload(sessions, sets_rows, session_volume_lookup),
    }


async def get_admin_revenue_data() -> dict[str, Any]:
    events = await _safe_request(
        "GET",
        "payment_events",
        params={
            "select": "event_type,phone_number,status,amount_inr,razorpay_payment_id,razorpay_subscription_id,occurred_at",
            "order": "occurred_at.desc",
        },
    )
    subscriptions = await _request(
        "GET",
        "subscriptions",
        params={"select": "user_id,status,expires_at,created_at"},
    )

    active_pro_count = sum(1 for row in _latest_subscription_by_user(subscriptions).values() if _is_subscription_active(row))
    mrr = float(active_pro_count * PRO_MONTHLY_PRICE_INR)

    successful_payments = [
        event for event in events if str(event.get("event_type")) in {"subscription.activated", "payment.captured"}
    ]
    cancelled_subscriptions = [event for event in events if str(event.get("event_type")) == "subscription.cancelled"]
    failed_payments = [event for event in events if str(event.get("event_type")) == "payment.failed"]

    total_revenue = sum(_to_float(event.get("amount_inr")) or float(PRO_MONTHLY_PRICE_INR) for event in successful_payments)

    return {
        "mrr": round(mrr, 2),
        "total_revenue_all_time": round(total_revenue, 2),
        "successful_payments": successful_payments,
        "cancelled_subscriptions": cancelled_subscriptions,
        "failed_payments": failed_payments,
    }


async def get_admin_live_sessions(limit: int = 80) -> dict[str, Any]:
    sessions = await _request(
        "GET",
        "sessions",
        params={
            "select": "id,user_id,logged_at,raw_message",
            "order": "logged_at.desc",
            "limit": str(limit),
        },
    )

    if not sessions:
        return {"sessions": []}

    session_ids = [str(row["id"]) for row in sessions if row.get("id")]
    user_ids = [str(row["user_id"]) for row in sessions if row.get("user_id")]
    sets_rows: list[dict[str, Any]] = []
    users: list[dict[str, Any]] = []

    if session_ids:
        sets_rows = await _request(
            "GET",
            "sets",
            params={
                "session_id": f"in.({','.join(session_ids)})",
                "select": "session_id,muscle_group,total_volume_kg,weight_kg,reps,sets_count",
            },
        )

    if user_ids:
        users = await _request(
            "GET",
            "users",
            params={
                "id": f"in.({','.join(user_ids)})",
                "select": "id,phone_number",
            },
        )

    phone_by_user = {str(row.get("id")): str(row.get("phone_number") or "") for row in users}
    grouped_sets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sets_rows:
        grouped_sets[str(row.get("session_id"))].append(row)

    output = []
    for session in sessions:
        session_id = str(session.get("id"))
        rows = grouped_sets.get(session_id, [])
        groups = sorted({str(row.get("muscle_group") or "Full Body") for row in rows})
        total_volume = 0.0
        for row in rows:
            volume = _to_float(row.get("total_volume_kg"))
            if volume is None:
                volume = _calc_volume(_to_float(row.get("weight_kg")), _to_int(row.get("reps")), _to_int(row.get("sets_count")))
            total_volume += volume

        phone = phone_by_user.get(str(session.get("user_id")), "")
        output.append(
            {
                "session_id": session_id,
                "time": session.get("logged_at"),
                "phone_number": phone,
                "phone_masked": _mask_phone_number(phone),
                "muscle_groups": groups,
                "total_volume": round(total_volume, 2),
            }
        )

    return {"sessions": output}


async def get_broadcast_targets(segment: str) -> list[str]:
    users, _, subscriptions = await _get_admin_base_rows()
    latest_subscriptions = _latest_subscription_by_user(subscriptions)

    segment_normalized = segment.strip().lower()
    targets: list[str] = []
    for user in users:
        user_id = str(user.get("id") or "")
        phone_number = str(user.get("phone_number") or "")
        if not user_id or not phone_number:
            continue

        subscription = latest_subscriptions.get(user_id)
        plan, status = _subscription_plan_status(subscription)

        include = False
        if segment_normalized == "all":
            include = True
        elif segment_normalized == "pro":
            include = plan == "pro" and status == "active"
        elif segment_normalized == "free":
            include = plan == "free" or status == "expired"

        if include:
            targets.append(phone_number)

    return targets
