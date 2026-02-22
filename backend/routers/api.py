from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from services.db import (
    get_exercise_history,
    get_medals_for_user,
    get_user_by_token,
    get_user_stats,
)
from services.image_gen import generate_story_card_png
from services.payments import create_razorpay_subscription, is_pro

router = APIRouter(prefix="/api", tags=["api"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail="Dashboard not found. Ask GymPulse on WhatsApp for your personal dashboard link.",
    )


async def _get_user_from_token(token: str) -> dict:
    if not token:
        raise _not_found()
    user = await get_user_by_token(token)
    if not user:
        raise _not_found()
    return user


async def _locked_payload(user: dict) -> dict:
    payment_url = None
    try:
        payment_url = await create_razorpay_subscription(user["id"], user["phone_number"])
    except Exception:
        payment_url = None

    return {
        "status": "locked",
        "message": "Your dashboard is a Pro feature.",
        "payment_url": payment_url,
    }


async def _ensure_pro_or_raise(user: dict) -> None:
    if await is_pro(user["id"]):
        return

    payload = await _locked_payload(user)
    raise HTTPException(
        status_code=403,
        detail=payload["message"],
        headers={"X-GymPulse-Payment-Url": payload.get("payment_url") or ""},
    )


@router.get("/dashboard/{token}")
async def get_dashboard(token: str) -> dict:
    user = await _get_user_from_token(token)
    if not await is_pro(user["id"]):
        return await _locked_payload(user)

    stats = await get_user_stats(user["id"])

    return {
        "status": "ok",
        "user": {
            "id": user["id"],
            "phone_number": user["phone_number"],
            "name": user.get("name"),
            "dashboard_token": user["dashboard_token"],
            "created_at": user.get("created_at"),
        },
        "stats": stats,
    }


@router.get("/exercises/{token}")
async def get_exercises(token: str) -> dict:
    user = await _get_user_from_token(token)
    await _ensure_pro_or_raise(user)
    return await get_exercise_history(user["id"])


@router.get("/medals/{token}")
async def get_medals(token: str) -> dict:
    user = await _get_user_from_token(token)
    await _ensure_pro_or_raise(user)
    return await get_medals_for_user(user["id"])


@router.get("/story/{token}")
async def get_story(token: str) -> StreamingResponse:
    user = await _get_user_from_token(token)
    await _ensure_pro_or_raise(user)
    stats = await get_user_stats(user["id"])
    image_bytes = generate_story_card_png(stats)

    return StreamingResponse(
        BytesIO(image_bytes),
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=story-card.png"},
    )
