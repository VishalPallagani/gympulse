import json
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-1.5-flash").strip()
GEMINI_API_BASE = (os.getenv("GEMINI_API_BASE") or "https://generativelanguage.googleapis.com").rstrip("/")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = (os.getenv("OLLAMA_MODEL") or "").strip()

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
MUSCLE_GROUP_MAP = {group.lower(): group for group in MUSCLE_GROUPS}
VALID_INTENTS = {
    "greeting",
    "question",
    "stats_request",
    "dashboard_request",
    "story_request",
    "medals_request",
    "unknown",
}

PROMPT_TEMPLATE = """You are a gym workout parser. The user will send a casual message describing their workout. Extract all exercises and return a JSON array. Each item should have:
- exercise_name (string, normalized, e.g. "Bench Press")
- muscle_group (string, one of: Chest, Back, Shoulders, Biceps, Triceps, Legs, Core, Cardio, Full Body)
- weight_kg (number or null if bodyweight)
- reps (number or null)
- sets_count (number or null)
- notes (string or null, e.g. "felt strong", "paused reps")

Parsing rules:
- If a message includes different weights/reps for the same exercise, output separate items for each scheme.
- Example: "bench 30kg x12, 35kg x10, 40kg x8" should return 3 Bench Press items with sets_count = 1 each.
- Example: "bench 3 reps 30kgs" means exercise=Bench Press, reps=3, weight_kg=30.
- Keep unknown numeric fields as null instead of guessing.

If the message is a bodyweight check-in, return {"type": "weight_log", "weight_kg": number}.
If the message is not a workout log, return {"type": "non_workout", "intent": "greeting/question/stats_request/dashboard_request/story_request/medals_request/unknown"}.

Message: {user_message}

Return only valid JSON. No explanation."""

MUSCLE_HINTS = {
    "Chest": ["bench", "incline", "decline", "chest", "fly", "press"],
    "Back": ["deadlift", "row", "pull up", "pulldown", "lat", "back"],
    "Shoulders": ["shoulder", "overhead press", "lateral raise", "rear delt", "arnold"],
    "Biceps": ["curl", "hammer curl", "biceps"],
    "Triceps": ["tricep", "pushdown", "skull crusher", "dips"],
    "Legs": ["squat", "leg press", "lunge", "hamstring", "calf", "rdl"],
    "Core": ["plank", "crunch", "ab wheel", "core"],
    "Cardio": ["run", "bike", "cardio", "jog", "rower", "walk"],
}

NON_WORKOUT_KEYWORDS = {
    "greeting": {"hi", "hello", "hey", "yo"},
    "stats_request": {"stats", "progress", "how am i doing"},
    "dashboard_request": {"dashboard", "link"},
    "story_request": {"story", "card"},
    "medals_request": {"medals", "badges"},
}

BODY_WEIGHT_KEYWORDS = {
    "weight",
    "weigh",
    "weighed",
    "weigh-in",
    "weigh in",
    "bodyweight",
    "body weight",
    "bw",
    "wt",
    "scale",
}

WORKOUT_TERMS = {
    "bench",
    "squat",
    "deadlift",
    "press",
    "row",
    "curl",
    "pull",
    "push",
    "lunge",
    "rdl",
    "fly",
    "extension",
    "raise",
    "dip",
    "lat",
    "pulldown",
    "split",
    "chest",
    "back",
    "legs",
    "shoulders",
    "triceps",
    "biceps",
    "cardio",
    "run",
    "walk",
    "bike",
}


class ParserError(RuntimeError):
    pass


def _extract_json_block(text: str) -> str:
    stripped = str(text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _to_number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_positive_int(value: Any) -> int | None:
    numeric = _to_number(value)
    if numeric is None:
        return None
    rounded = int(round(numeric))
    if rounded <= 0:
        return None
    return rounded


def _infer_muscle_group(exercise_name: str) -> str:
    lowered = exercise_name.lower()
    for muscle_group, keywords in MUSCLE_HINTS.items():
        if any(keyword in lowered for keyword in keywords):
            return muscle_group
    return "Full Body"


def _normalize_muscle_group(value: Any, exercise_name: str) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in MUSCLE_GROUP_MAP:
        return MUSCLE_GROUP_MAP[cleaned]
    return _infer_muscle_group(exercise_name)


def _normalize_exercise_name(value: Any) -> str:
    name = " ".join(str(value or "").strip().split())
    return " ".join(word.capitalize() for word in name.split())


def _normalize_exercise(item: dict[str, Any]) -> dict[str, Any] | None:
    exercise_name = _normalize_exercise_name(item.get("exercise_name"))
    if not exercise_name:
        return None

    weight_kg = _to_number(item.get("weight_kg"))
    if weight_kg is not None and weight_kg <= 0:
        weight_kg = None
    if weight_kg is not None:
        weight_kg = round(weight_kg, 2)

    reps = _to_positive_int(item.get("reps"))
    sets_count = _to_positive_int(item.get("sets_count"))
    if sets_count is None and reps is not None and weight_kg is not None:
        sets_count = 1

    notes = item.get("notes")
    notes_value = str(notes).strip() if notes is not None else None
    if notes_value == "":
        notes_value = None

    return {
        "exercise_name": exercise_name,
        "muscle_group": _normalize_muscle_group(item.get("muscle_group"), exercise_name),
        "weight_kg": weight_kg,
        "reps": reps,
        "sets_count": sets_count,
        "notes": notes_value,
    }


def _normalize_non_workout(intent: Any) -> dict[str, str]:
    cleaned = str(intent or "unknown").strip().lower()
    if cleaned not in VALID_INTENTS:
        cleaned = "unknown"
    return {"type": "non_workout", "intent": cleaned}


def _normalize_llm_result(payload: Any) -> list[dict[str, Any]] | dict[str, Any]:
    if isinstance(payload, list):
        normalized = []
        for item in payload:
            if isinstance(item, dict):
                normalized_item = _normalize_exercise(item)
                if normalized_item:
                    normalized.append(normalized_item)
        return normalized if normalized else _normalize_non_workout("unknown")

    if not isinstance(payload, dict):
        return _normalize_non_workout("unknown")

    payload_type = str(payload.get("type", "")).strip().lower()
    if payload_type == "weight_log":
        parsed_weight = _to_number(payload.get("weight_kg"))
        if parsed_weight is not None and 25 <= parsed_weight <= 300:
            return {"type": "weight_log", "weight_kg": round(parsed_weight, 1)}
        return _normalize_non_workout("unknown")

    if payload_type == "non_workout":
        return _normalize_non_workout(payload.get("intent"))

    if isinstance(payload.get("exercises"), list):
        return _normalize_llm_result(payload["exercises"])

    if payload.get("exercise_name"):
        single = _normalize_exercise(payload)
        return [single] if single else _normalize_non_workout("unknown")

    if payload.get("intent"):
        return _normalize_non_workout(payload.get("intent"))

    return _normalize_non_workout("unknown")


def _detect_non_workout_intent(user_message: str) -> dict[str, str] | None:
    lowered = user_message.lower().strip()
    if "?" in lowered or lowered.startswith(("how", "what", "can", "should", "when", "why")):
        return {"type": "non_workout", "intent": "question"}

    for intent, keywords in NON_WORKOUT_KEYWORDS.items():
        if lowered in keywords or any(f" {keyword} " in f" {lowered} " for keyword in keywords):
            return {"type": "non_workout", "intent": intent}

    if len(lowered.split()) <= 3 and not re.search(r"\d", lowered):
        return {"type": "non_workout", "intent": "greeting"}

    return None


def _extract_body_weight_kg(user_message: str) -> float | None:
    lowered = user_message.lower().strip()
    if not lowered:
        return None

    if re.search(r"\d+\s*x\s*\d+", lowered):
        return None

    has_weight_keyword = any(keyword in lowered for keyword in BODY_WEIGHT_KEYWORDS)
    standalone_weight = bool(
        re.fullmatch(
            r"\s*\d+(?:\.\d+)?\s*(kg|kgs|kilograms?|lb|lbs|pounds?)?\s*",
            lowered,
        )
    )
    if not has_weight_keyword and not standalone_weight:
        return None

    mentions_workout_term = any(term in lowered for term in WORKOUT_TERMS)
    if mentions_workout_term and not any(keyword in lowered for keyword in {"my weight", "body weight", "weigh in"}):
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|lb|lbs|pounds?)?", lowered)
    if not match:
        return None

    raw_value = float(match.group(1))
    if raw_value <= 0:
        return None

    unit = (match.group(2) or "kg").lower()
    weight_kg = raw_value * 0.45359237 if unit.startswith("lb") or unit.startswith("pound") else raw_value
    if weight_kg < 25 or weight_kg > 300:
        return None
    return round(weight_kg, 1)


def _extract_exercise_label(segment: str) -> str:
    without_numbers = re.sub(r"\d+(?:\.\d+)?", " ", segment)
    without_units = re.sub(r"\b(kg|kgs|kilograms?|lb|lbs|pounds?|reps?|sets?|x|@|at)\b", " ", without_numbers, flags=re.I)
    cleaned = re.sub(r"[^a-zA-Z\s+/&'-]", " ", without_units)
    cleaned = " ".join(cleaned.split()).strip(" -:")
    return _normalize_exercise_name(cleaned)


def _parse_weight_rep_schemes(segment: str) -> list[tuple[float, int, int]]:
    schemes: list[tuple[float, int, int]] = []

    # Matches forms like "30kg x 8".
    for weight_raw, reps_raw in re.findall(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)\s*[xX]\s*(\d+)", segment, flags=re.I):
        weight = float(weight_raw)
        reps = int(reps_raw)
        if weight > 0 and reps > 0:
            schemes.append((weight, reps, 1))

    explicit_weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)", segment, flags=re.I)
    if explicit_weight_match and not schemes:
        # Handles forms like "120kg 3x5" where x-pattern means sets x reps.
        set_rep = re.search(r"(\d+)\s*[xX]\s*(\d+)", segment)
        if set_rep:
            weight = float(explicit_weight_match.group(1))
            sets_count = int(set_rep.group(1))
            reps = int(set_rep.group(2))
            if weight > 0 and reps > 0 and sets_count > 0:
                schemes.append((weight, reps, sets_count))

    if not explicit_weight_match:
        # Matches shorthand forms like "30 x 8" when no kg token is present.
        for weight_raw, reps_raw in re.findall(r"(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)", segment):
            weight = float(weight_raw)
            reps = int(reps_raw)
            if weight > 0 and reps > 0:
                schemes.append((weight, reps, 1))

    # Matches forms like "3 reps 30kg" or "3 rep @ 30kg".
    for reps_raw, weight_raw in re.findall(r"(\d+)\s*reps?\s*(?:at|@)?\s*(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)", segment, flags=re.I):
        weight = float(weight_raw)
        reps = int(reps_raw)
        if weight > 0 and reps > 0:
            schemes.append((weight, reps, 1))

    # Matches forms like "30kg 3 reps".
    for weight_raw, reps_raw in re.findall(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)\s*(\d+)\s*reps?", segment, flags=re.I):
        weight = float(weight_raw)
        reps = int(reps_raw)
        if weight > 0 and reps > 0:
            schemes.append((weight, reps, 1))

    unique: list[tuple[float, int, int]] = []
    seen = set()
    for item in schemes:
        marker = (round(item[0], 2), item[1], item[2])
        if marker not in seen:
            seen.add(marker)
            unique.append((round(item[0], 2), item[1], item[2]))
    return unique


def _simple_regex_parse(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    weight_kg = _extract_body_weight_kg(user_message)
    if weight_kg is not None:
        return {"type": "weight_log", "weight_kg": weight_kg}

    intent = _detect_non_workout_intent(user_message)
    if intent:
        return intent

    segments = [segment.strip() for segment in re.split(r",|;|\n", user_message) if segment.strip()]
    parsed: list[dict[str, Any]] = []
    active_exercise = ""

    for segment in segments:
        exercise_name = _extract_exercise_label(segment)
        if exercise_name:
            active_exercise = exercise_name
        elif active_exercise:
            exercise_name = active_exercise

        if not exercise_name:
            continue

        schemes = _parse_weight_rep_schemes(segment)
        if schemes:
            for weight_value, reps_value, sets_value in schemes:
                parsed.append(
                    {
                        "exercise_name": exercise_name,
                        "muscle_group": _infer_muscle_group(exercise_name),
                        "weight_kg": weight_value,
                        "reps": reps_value,
                        "sets_count": sets_value,
                        "notes": None,
                    }
                )
            continue

        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)", segment, flags=re.I)
        set_rep_match = re.search(r"(\d+)\s*[xX]\s*(\d+)", segment)
        reps_match = re.search(r"(\d+)\s*reps?", segment, flags=re.I)
        sets_match = re.search(r"(\d+)\s*sets?", segment, flags=re.I)

        weight_value = float(weight_match.group(1)) if weight_match else None
        sets_count = int(set_rep_match.group(1)) if set_rep_match else (int(sets_match.group(1)) if sets_match else None)
        reps_value = int(set_rep_match.group(2)) if set_rep_match else (int(reps_match.group(1)) if reps_match else None)
        if sets_count is None and reps_value is not None and weight_value is not None:
            sets_count = 1

        parsed.append(
            {
                "exercise_name": exercise_name,
                "muscle_group": _infer_muscle_group(exercise_name),
                "weight_kg": weight_value,
                "reps": reps_value,
                "sets_count": sets_count,
                "notes": None,
            }
        )

    if not parsed:
        return _normalize_non_workout("unknown")
    return parsed


def _parse_json_response(raw_text: str) -> Any:
    try:
        return json.loads(_extract_json_block(raw_text))
    except json.JSONDecodeError as exc:
        logger.error("Parser model returned invalid JSON: %s", raw_text)
        raise ParserError("Could not parse workout message.") from exc


async def _parse_with_gemini(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    if not GEMINI_API_KEY:
        raise ParserError("Gemini API key is not configured.")

    prompt = PROMPT_TEMPLATE.format(user_message=user_message)
    url = f"{GEMINI_API_BASE}/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "topP": 0.9,
        },
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url, params={"key": GEMINI_API_KEY}, json=payload)

    if response.status_code >= 400:
        logger.error("Gemini parse failed (%s): %s", response.status_code, response.text)
        raise ParserError("Could not parse workout message.")

    data = response.json()
    raw_text = ""
    try:
        raw_text = str(data["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as exc:
        logger.error("Unexpected Gemini response: %s", data)
        raise ParserError("Could not parse workout message.") from exc

    return _normalize_llm_result(_parse_json_response(raw_text))


async def _parse_with_ollama(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(user_message=user_message)
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload)

    if response.status_code >= 400:
        logger.error("Ollama parse failed (%s): %s", response.status_code, response.text)
        raise ParserError("Could not parse workout message.")

    data = response.json()
    raw_text = data.get("response")
    if not raw_text:
        logger.error("Unexpected Ollama response: %s", data)
        raise ParserError("Could not parse workout message.")

    return _normalize_llm_result(_parse_json_response(str(raw_text)))


async def parse_workout_message(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    cleaned = str(user_message or "").strip()
    if not cleaned:
        return _normalize_non_workout("unknown")

    body_weight = _extract_body_weight_kg(cleaned)
    if body_weight is not None:
        return {"type": "weight_log", "weight_kg": body_weight}

    quick_intent = _detect_non_workout_intent(cleaned)
    if quick_intent:
        return quick_intent

    if GEMINI_API_KEY:
        try:
            return await _parse_with_gemini(cleaned)
        except (ParserError, httpx.HTTPError, OSError, ValueError) as exc:
            logger.warning("Gemini parser failed, trying fallback parser: %s", exc)

    if OLLAMA_MODEL:
        try:
            return await _parse_with_ollama(cleaned)
        except (ParserError, httpx.HTTPError, OSError, ValueError) as exc:
            logger.warning("Ollama parser failed, trying regex parser: %s", exc)

    fallback = _simple_regex_parse(cleaned)
    if isinstance(fallback, list) and fallback:
        return fallback
    if isinstance(fallback, dict) and fallback.get("type") in {"weight_log", "non_workout"}:
        return fallback

    raise ParserError("Could not parse workout message.")
