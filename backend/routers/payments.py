import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

from services.db import get_user_by_id
from services.payments import (
    PaymentsConfigError,
    PaymentsWebhookError,
    create_razorpay_subscription,
    verify_payment_webhook,
)
from services.whatsapp import send_text

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])
_raw_frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").strip()
if _raw_frontend_url and "://" not in _raw_frontend_url:
    _raw_frontend_url = f"https://{_raw_frontend_url}"
FRONTEND_URL = _raw_frontend_url.rstrip("/")


def _dashboard_url(token: str) -> str:
    return f"{FRONTEND_URL.rstrip('/')}/dashboard/{token}"


@router.post("/payments/webhook")
async def razorpay_webhook(request: Request) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    try:
        event_result = await verify_payment_webhook(payload, signature)
    except PaymentsWebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PaymentsConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Razorpay webhook failed unexpectedly")
        raise HTTPException(status_code=500, detail="Unable to process payment webhook.") from exc

    event_type = event_result.get("event_type")
    user_id = event_result.get("user_id")
    phone_number = event_result.get("phone_number")

    if user_id:
        user = await get_user_by_id(user_id)
    else:
        user = None

    if user and not phone_number:
        phone_number = user.get("phone_number")

    dashboard_link = _dashboard_url(user["dashboard_token"]) if user else None

    if event_type == "subscription.activated" and phone_number and dashboard_link:
        try:
            await send_text(
                phone_number,
                f"\U0001F389 Welcome to GymPulse Pro! Your dashboard is live: {dashboard_link}. "
                "Your gains are about to look incredible \U0001F4AA",
            )
        except Exception:
            logger.exception("Failed to send subscription.activated message to %s", phone_number)
    elif event_type == "subscription.cancelled" and phone_number:
        try:
            await send_text(
                phone_number,
                "Your Pro subscription has ended. Your workout logs are safe - "
                "upgrade anytime to get your dashboard back.",
            )
        except Exception:
            logger.exception("Failed to send subscription.cancelled message to %s", phone_number)
    elif event_type == "payment.failed" and phone_number and user_id:
        try:
            retry_link = await create_razorpay_subscription(user_id, phone_number)
            await send_text(
                phone_number,
                f"Your payment failed. Try again here: {retry_link}",
            )
        except Exception:
            logger.exception("Failed to send payment.failed message to %s", phone_number)

    return {"status": "ok"}
