import json
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

PROMPT_TEMPLATE = """You are a gym workout parser. The user will send a casual message describing their workout. Extract all exercises and return a JSON array. Each item should have:
- exercise_name (string, normalized, e.g. "Bench Press")
- muscle_group (string, one of: Chest, Back, Shoulders, Biceps, Triceps, Legs, Core, Cardio, Full Body)
- weight_kg (number or null if bodyweight)
- reps (number or null)
- sets_count (number or null)
- notes (string or null, e.g. "felt strong", "paused reps")

If the message is a bodyweight check-in, return {"type": "weight_log", "weight_kg": number}.
If the message is not a workout log, return {"type": "non_workout", "intent": "greeting/question/stats_request/dashboard_request/story_request/medals_request/unknown"}.

Message: {user_message}

Return only valid JSON. No explanation."""

MUSCLE_HINTS = {
    "Chest": ["bench", "incline", "decline", "chest", "fly", "press"],
    "Back": ["deadlift", "row", "pull up", "lat pulldown", "back"],
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
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _normalize_exercise(item: dict[str, Any]) -> dict[str, Any]:
    name = " ".join(str(item.get("exercise_name", "")).strip().split())
    item["exercise_name"] = " ".join(part.capitalize() for part in name.split())
    return item


def _infer_muscle_group(exercise_name: str) -> str:
    lowered = exercise_name.lower()
    for muscle_group, keywords in MUSCLE_HINTS.items():
        if any(keyword in lowered for keyword in keywords):
            return muscle_group
    return "Full Body"


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

    # Guardrails: avoid misclassifying normal workout logs that include lifted weight.
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


def _simple_regex_parse(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    weight_kg = _extract_body_weight_kg(user_message)
    if weight_kg is not None:
        return {"type": "weight_log", "weight_kg": weight_kg}

    intent = _detect_non_workout_intent(user_message)
    if intent:
        return intent

    segments = [segment.strip() for segment in re.split(r",|;|\n", user_message) if segment.strip()]
    parsed: list[dict[str, Any]] = []

    for segment in segments:
        # Examples handled: "bench 80kg 4x8", "pull ups 3x10", "run 30min"
        lower_segment = segment.lower()
        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*kg", lower_segment)
        set_rep_match = re.search(r"(\d+)\s*x\s*(\d+)", lower_segment)

        exercise_name = re.sub(r"\d+(?:\.\d+)?\s*kg", "", segment, flags=re.IGNORECASE)
        exercise_name = re.sub(r"\d+\s*x\s*\d+", "", exercise_name, flags=re.IGNORECASE)
        exercise_name = re.sub(r"[-\u2013\u2014]", " ", exercise_name).strip()
        exercise_name = " ".join(exercise_name.split())

        if not exercise_name:
            continue

        parsed.append(
            {
                "exercise_name": " ".join(word.capitalize() for word in exercise_name.split()),
                "muscle_group": _infer_muscle_group(exercise_name),
                "weight_kg": float(weight_match.group(1)) if weight_match else None,
                "reps": int(set_rep_match.group(2)) if set_rep_match else None,
                "sets_count": int(set_rep_match.group(1)) if set_rep_match else None,
                "notes": None,
            }
        )

    if not parsed:
        return {"type": "non_workout", "intent": "unknown"}
    return parsed


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

    try:
        parsed = json.loads(_extract_json_block(str(raw_text)))
    except json.JSONDecodeError as exc:
        logger.error("Ollama returned invalid JSON: %s", raw_text)
        raise ParserError("Could not parse workout message.") from exc

    if isinstance(parsed, list):
        return [_normalize_exercise(item) for item in parsed if isinstance(item, dict)]

    if isinstance(parsed, dict):
        parsed_type = str(parsed.get("type", "")).strip().lower()
        if parsed_type == "weight_log":
            parsed_weight = _to_number(parsed.get("weight_kg"))
            if parsed_weight is not None and 25 <= parsed_weight <= 300:
                return {"type": "weight_log", "weight_kg": round(parsed_weight, 1)}
            return {"type": "non_workout", "intent": "unknown"}
        if isinstance(parsed.get("exercises"), list):
            return [_normalize_exercise(item) for item in parsed["exercises"] if isinstance(item, dict)]
        return parsed

    return {"type": "non_workout", "intent": "unknown"}


def _to_number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


async def parse_workout_message(user_message: str) -> list[dict[str, Any]] | dict[str, Any]:
    if not user_message or not user_message.strip():
        return {"type": "non_workout", "intent": "unknown"}

    weight_kg = _extract_body_weight_kg(user_message)
    if weight_kg is not None:
        return {"type": "weight_log", "weight_kg": weight_kg}

    if not OLLAMA_MODEL:
        return _simple_regex_parse(user_message)

    try:
        return await _parse_with_ollama(user_message)
    except ParserError as parser_error:
        fallback = _simple_regex_parse(user_message)
        if isinstance(fallback, list) and fallback:
            return fallback
        if isinstance(fallback, dict) and str(fallback.get("intent")) in {
            "greeting",
            "question",
            "stats_request",
            "dashboard_request",
        }:
            return fallback
        # If neither the open-source LLM nor the fallback can parse, bubble up
        # so WhatsApp can ask the user to rephrase.
        raise parser_error
