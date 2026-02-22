import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from services.db import (
    check_and_award_medals,
    get_dashboard_link_by_phone,
    get_medals_for_user,
    get_or_create_user,
    get_user_stats,
    get_weekly_muscle_group_change,
    mark_weight_prompted_today,
    save_body_weight_log,
    save_session,
    should_prompt_for_weight,
    update_personal_records,
)
from services.image_gen import generate_story_card_png
from services.parser import ParserError, parse_workout_message
from services.payments import create_razorpay_subscription, is_pro
from services.whatsapp import send_image, send_text

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
_raw_frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").strip()
if _raw_frontend_url and "://" not in _raw_frontend_url:
    _raw_frontend_url = f"https://{_raw_frontend_url}"
FRONTEND_URL = _raw_frontend_url.rstrip("/")


def _format_int(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return "0"


def _format_weight(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "0.0"


def _format_delta(value: Any) -> str:
    try:
        delta = float(value)
    except Exception:
        return "0.0"
    return f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"


def _dashboard_url(token: str) -> str:
    return f"{FRONTEND_URL.rstrip('/')}/dashboard/{token}"


def _muscle_summary(exercises: list[dict[str, Any]]) -> str:
    muscles = sorted({str(item.get("muscle_group", "Full Body")) for item in exercises if item.get("muscle_group")})
    if not muscles:
        return "Session"
    if len(muscles) == 1:
        return f"{muscles[0]} session"
    if len(muscles) == 2:
        return f"{muscles[0]} & {muscles[1]} session"
    return f"{muscles[0]}, {muscles[1]} + {len(muscles) - 2} more"


def _keyword_match(text: str, keyword: str) -> bool:
    normalized = text.lower().strip()
    cleaned = "".join(char for char in normalized if char.isalnum() or char.isspace()).strip()
    return cleaned == keyword or cleaned.startswith(f"{keyword} ") or f" {keyword}" in cleaned


async def _generate_payment_link(user: dict[str, Any]) -> str | None:
    try:
        return await create_razorpay_subscription(user["id"], user["phone_number"])
    except Exception:
        logger.exception("Failed to create Razorpay subscription link for user %s", user.get("id"))
        return None


async def _send_dashboard_paywall(phone_number: str, user: dict[str, Any]) -> None:
    payment_link = await _generate_payment_link(user)
    link_block = payment_link if payment_link else "Payment link is temporarily unavailable. Please try again shortly."
    message = (
        "Your dashboard is a Pro feature \U0001F4CA\n\n"
        "Unlock beautiful charts, share drops and progress tracking for just \u20B999/month \U0001F447\n\n"
        f"{link_block}\n\n"
        "Your workouts are already being tracked - you just need to unlock the view \U0001F513"
    )
    await send_text(phone_number, message)


async def _send_story_paywall(phone_number: str, user: dict[str, Any]) -> None:
    payment_link = await _generate_payment_link(user)
    link_block = payment_link if payment_link else "Payment link is temporarily unavailable. Please try again shortly."
    message = (
        "Your dashboard is a Pro feature \U0001F4CA\n\n"
        "Unlock beautiful charts, weekly share drops and medals for just \u20B999/month \U0001F447\n\n"
        f"{link_block}\n\n"
        "Your workouts are already being tracked - you just need to unlock the view \U0001F513"
    )
    await send_text(phone_number, message)


async def _send_stats(phone_number: str, user_id: str) -> None:
    stats = await get_user_stats(user_id)
    quick = stats.get("quick_stats", {})
    latest_weight = quick.get("latest_weight_kg")
    weight_delta_7d = quick.get("weight_delta_7d_kg")
    weight_line = "- Bodyweight: not logged yet"
    if latest_weight is not None:
        if weight_delta_7d is None:
            weight_line = f"- Bodyweight: {_format_weight(latest_weight)} kg"
        else:
            weight_line = (
                f"- Bodyweight: {_format_weight(latest_weight)} kg "
                f"(7-day {_format_delta(weight_delta_7d)} kg)"
            )

    message = (
        "\U0001F4CA Your week:\n"
        f"- {quick.get('sessions', 0)} sessions\n"
        f"- {_format_int(quick.get('total_volume', 0))} kg total volume\n"
        f"- Strongest day: {quick.get('strongest_day', 'N/A')}\n"
        f"- Most trained: {quick.get('most_trained', 'N/A')}\n"
        f"- Current streak: {quick.get('current_streak', 0)} days \U0001F525\n"
        f"{weight_line}"
    )
    await send_text(phone_number, message)


async def _send_medals(phone_number: str, user_id: str) -> None:
    medals_data = await get_medals_for_user(user_id)
    earned = medals_data.get("earned", [])

    if not earned:
        await send_text(
            phone_number,
            "No medals yet. Keep logging sessions and they will unlock automatically \U0001F3C5",
        )
        return

    lines = ["\U0001F3C5 Your medals:"]
    for medal in earned:
        emoji = medal.get("medal_emoji") or "\U0001F3C5"
        lines.append(f"- {emoji} {medal.get('medal_name')}")
    await send_text(phone_number, "\n".join(lines))


async def _send_story(phone_number: str, user_id: str) -> None:
    stats = await get_user_stats(user_id)
    image_bytes = generate_story_card_png(stats)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name

        await send_image(phone_number, temp_path)
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                logger.exception("Failed to delete temporary story image: %s", temp_path)


async def _maybe_send_daily_weight_prompt(phone_number: str, user: dict[str, Any]) -> None:
    try:
        if not await should_prompt_for_weight(user):
            return

        await send_text(
            phone_number,
            "Quick check-in: send today's bodyweight like 'weight 78.4kg'. I will track trend and cut/bulk pace for you.",
        )
        await mark_weight_prompted_today(user["id"])
    except Exception:
        logger.exception("Failed to send daily weight prompt for user %s", user.get("id"))


async def _handle_weight_log(phone_number: str, user_id: str, weight_kg: Any) -> None:
    try:
        result = await save_body_weight_log(user_id, float(weight_kg), source="whatsapp")
    except ValueError:
        await send_text(
            phone_number,
            "That weight looks out of range. Send it like 'weight 78.4kg'.",
        )
        return
    except Exception as exc:
        logger.exception("Failed to save body weight for user %s", user_id)
        if "404" in str(exc):
            await send_text(
                phone_number,
                "Weight tracking is not fully enabled yet on the server. Please ask admin to run the latest database schema migration.",
            )
            return
        await send_text(
            phone_number,
            "I could not save your weight right now. Please try again in a moment.",
        )
        return

    summary = result.get("summary", {})
    latest_weight = summary.get("latest_weight_kg")
    delta_last = summary.get("delta_vs_last_log_kg")
    delta_7d = summary.get("delta_7d_kg")
    adherence = summary.get("adherence_30d_pct")

    lines = [f"\u2705 Bodyweight logged: {_format_weight(latest_weight)} kg"]
    if delta_last is not None:
        lines.append(f"Compared to last log: {_format_delta(delta_last)} kg")
    if delta_7d is not None:
        lines.append(f"7-day change: {_format_delta(delta_7d)} kg")
    lines.append(f"30-day logging consistency: {int(round(float(adherence or 0)))}%")
    lines.append("Keep logging daily for better coaching accuracy.")
    await send_text(phone_number, "\n".join(lines))


async def _send_dashboard(phone_number: str, user: dict[str, Any]) -> None:
    if await is_pro(user["id"]):
        link = await get_dashboard_link_by_phone(phone_number)
        if link:
            await send_text(phone_number, f"Your dashboard: {link}")
        else:
            await send_text(phone_number, f"Your dashboard: {_dashboard_url(user['dashboard_token'])}")
        return
    await _send_dashboard_paywall(phone_number, user)


async def _handle_non_workout(phone_number: str, user_id: str, user: dict[str, Any], intent: str) -> None:
    if intent == "stats_request":
        await _send_stats(phone_number, user_id)
        return

    if intent == "dashboard_request":
        await _send_dashboard(phone_number, user)
        return

    if intent in {"greeting", "question"}:
        await send_text(
            phone_number,
            "Hey! Send your workout like this: 'back day - deadlift 100kg 3x5, pull ups 3x10'.",
        )
        return

    if intent == "story_request":
        if await is_pro(user_id):
            await _send_story(phone_number, user_id)
        else:
            await _send_story_paywall(phone_number, user)
        return

    if intent == "medals_request":
        await _send_medals(phone_number, user_id)
        return

    await send_text(
        phone_number,
        "Didn't quite get that! Just text me your workout. Example: 'back day - deadlift 100kg 3x5, pull ups 3x10, seated row 60kg 4x8'",
    )


async def _handle_workout(phone_number: str, user_id: str, raw_text: str, exercises: list[dict[str, Any]]) -> None:
    session_result = await save_session(user_id, raw_text, exercises)
    new_prs = await update_personal_records(user_id, exercises)
    new_medals = await check_and_award_medals(user_id)

    muscle_groups = sorted({item.get("muscle_group") for item in exercises if item.get("muscle_group")})
    primary_muscle = muscle_groups[0] if muscle_groups else None
    change = await get_weekly_muscle_group_change(user_id, primary_muscle) if primary_muscle else None

    lines = [
        f"\u2705 Logged! {_muscle_summary(exercises)} saved.",
        "",
        f"\U0001F4CA Today's volume: {_format_int(session_result.get('total_volume', 0))} kg",
    ]

    for pr in new_prs[:2]:
        lines.append(f"\U0001F525 {pr['exercise_name']}: {_format_int(pr['weight_kg'])}kg (new PR! \U0001F3C6)")

    if change is not None:
        trend = "up" if change >= 0 else "down"
        lines.append(f"\U0001F4C8 {primary_muscle} volume {trend} {abs(change)}% vs last week")

    if new_medals:
        lines.append("")
        lines.append("\U0001F3C5 New medals unlocked:")
        for medal in new_medals:
            emoji = medal.get("medal_emoji") or "\U0001F3C5"
            lines.append(f"- {emoji} {medal.get('medal_name')}")

    lines.append("")
    lines.append("Keep pushing \U0001F4A5")

    await send_text(phone_number, "\n".join(lines))


async def _handle_text_message(phone_number: str, message_text: str, display_name: str | None = None) -> None:
    user, _ = await get_or_create_user(phone_number, name=display_name)
    user_id = user["id"]
    normalized = message_text.lower().strip()
    should_prompt_weight = True

    if _keyword_match(normalized, "dashboard"):
        await _send_dashboard(phone_number, user)
    elif _keyword_match(normalized, "stats"):
        await _send_stats(phone_number, user_id)
    elif _keyword_match(normalized, "story"):
        if await is_pro(user_id):
            await _send_story(phone_number, user_id)
        else:
            await _send_story_paywall(phone_number, user)
    elif _keyword_match(normalized, "medals"):
        await _send_medals(phone_number, user_id)
    else:
        try:
            parsed = await parse_workout_message(message_text)
        except ParserError:
            await send_text(
                phone_number,
                "I couldn't parse that workout yet. Try one of these:\n"
                "- bench 80kg 4x8, dips 3x12\n"
                "- i did 30kg bench press\n"
                "- bench 30kg x12, 35kg x10, 40kg x8",
            )
            should_prompt_weight = False
            parsed = None

        if parsed is not None:
            if isinstance(parsed, dict):
                parsed_type = str(parsed.get("type", "")).strip().lower()
                if parsed_type == "weight_log":
                    await _handle_weight_log(phone_number, user_id, parsed.get("weight_kg"))
                    should_prompt_weight = False
                else:
                    intent = str(parsed.get("intent", "unknown"))
                    await _handle_non_workout(phone_number, user_id, user, intent)
            elif not parsed:
                await send_text(
                    phone_number,
                    "Didn't quite get that! Just text me your workout. Example: 'back day - deadlift 100kg 3x5, pull ups 3x10, seated row 60kg 4x8'",
                )
            else:
                await _handle_workout(phone_number, user_id, message_text, parsed)

    if should_prompt_weight:
        await _maybe_send_daily_weight_prompt(phone_number, user)


@router.get("/webhook")
async def verify_webhook(request: Request) -> PlainTextResponse:
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")

    if mode == "subscribe" and verify_token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@router.post("/webhook")
async def receive_webhook(payload: dict[str, Any]) -> dict[str, str]:
    entries = payload.get("entry", [])

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            contacts = value.get("contacts", []) or []
            contact_name_by_phone: dict[str, str] = {}
            for contact in contacts:
                wa_id = "".join(char for char in str(contact.get("wa_id", "")) if char.isdigit())
                profile_name = str((contact.get("profile") or {}).get("name") or "").strip()
                if wa_id and profile_name:
                    contact_name_by_phone[wa_id] = profile_name

            for message in value.get("messages", []):
                phone_number = message.get("from")
                msg_type = message.get("type")

                if not phone_number:
                    continue

                if msg_type != "text":
                    await send_text(
                        phone_number,
                        "Send text workouts only for now. Example: 'squat 90kg 5x5, leg press 180kg 4x10'.",
                    )
                    continue

                text_body = message.get("text", {}).get("body", "").strip()
                if not text_body:
                    continue

                try:
                    normalized_phone = "".join(char for char in str(phone_number) if char.isdigit())
                    await _handle_text_message(
                        phone_number,
                        text_body,
                        display_name=contact_name_by_phone.get(normalized_phone),
                    )
                except Exception:
                    logger.exception("Failed to handle incoming WhatsApp message")
                    await send_text(
                        phone_number,
                        "Something went wrong on my side. Please try again in a moment.",
                    )

    return {"status": "ok"}
