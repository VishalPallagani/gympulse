import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

from services.db import (
    get_subscription_by_razorpay,
    get_subscription_for_user,
    is_user_pro,
    log_payment_event,
    upsert_subscription_for_user,
)

load_dotenv()

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_PLAN_ID = os.getenv("RAZORPAY_PLAN_ID", "")
RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"


class PaymentsConfigError(RuntimeError):
    pass


class PaymentsWebhookError(RuntimeError):
    pass


def _ensure_key_config() -> None:
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or not RAZORPAY_PLAN_ID:
        raise PaymentsConfigError(
            "Razorpay is not configured. Set RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, and RAZORPAY_PLAN_ID."
        )


def _ensure_webhook_config() -> None:
    if not RAZORPAY_WEBHOOK_SECRET:
        raise PaymentsConfigError("Razorpay webhook secret is missing. Set RAZORPAY_WEBHOOK_SECRET.")


def _basic_auth_header() -> str:
    token = base64.b64encode(f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def _normalize_phone(phone_number: str) -> str:
    return "".join(char for char in str(phone_number) if char.isdigit())


def _from_unix(seconds: Any) -> str | None:
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(int(seconds), tz=timezone.utc).isoformat()
    except Exception:
        return None


async def _razorpay_request(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_key_config()
    url = f"{RAZORPAY_BASE_URL}/{path.lstrip('/')}"
    headers = {"Authorization": _basic_auth_header(), "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(method=method, url=url, headers=headers, json=payload)

    if response.status_code >= 400:
        logger.error("Razorpay API error (%s): %s", response.status_code, response.text)
        raise RuntimeError("Razorpay request failed.")

    return response.json()


async def _razorpay_get(path: str) -> dict[str, Any]:
    _ensure_key_config()
    url = f"{RAZORPAY_BASE_URL}/{path.lstrip('/')}"
    headers = {"Authorization": _basic_auth_header()}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url=url, headers=headers)

    if response.status_code >= 400:
        logger.error("Razorpay API error (%s): %s", response.status_code, response.text)
        raise RuntimeError("Razorpay request failed.")

    return response.json()


async def create_razorpay_subscription(user_id: str, phone_number: str) -> str:
    existing = await get_subscription_for_user(user_id)
    existing_subscription_id = str(existing.get("razorpay_subscription_id") or "") if existing else ""
    existing_status = str(existing.get("status") or "").lower() if existing else ""
    if existing_subscription_id and existing_status in {"created", "authenticated", "pending", "payment_failed"}:
        try:
            current_subscription = await _razorpay_get(f"subscriptions/{existing_subscription_id}")
            current_short_url = current_subscription.get("short_url")
            if current_short_url:
                return str(current_short_url)
        except Exception:
            logger.exception("Failed to fetch existing Razorpay subscription URL")

    normalized_phone = _normalize_phone(phone_number)
    customer = await _razorpay_request(
        "POST",
        "customers",
        {
            "name": "GymPulse User",
            "contact": normalized_phone[-15:] if normalized_phone else "0000000000",
            "fail_existing": 0,
            "notes": {"user_id": user_id},
        },
    )
    customer_id = customer.get("id")

    subscription = await _razorpay_request(
        "POST",
        "subscriptions",
        {
            "plan_id": RAZORPAY_PLAN_ID,
            "total_count": 120,
            "quantity": 1,
            "customer_notify": 1,
            "customer_id": customer_id,
            "notes": {"user_id": user_id, "phone_number": phone_number},
        },
    )

    status = str(subscription.get("status") or "created")
    is_active = status.lower() == "active"
    started_at = _from_unix(subscription.get("current_start")) or (datetime.now(timezone.utc).isoformat() if is_active else None)
    expires_at = _from_unix(subscription.get("current_end")) or (
        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat() if is_active else None
    )

    await upsert_subscription_for_user(
        user_id,
        {
            "razorpay_subscription_id": subscription.get("id"),
            "razorpay_customer_id": customer_id,
            "status": status,
            "plan": "pro",
            "started_at": started_at,
            "expires_at": expires_at,
        },
    )
    await log_payment_event(
        event_type="subscription.created",
        user_id=user_id,
        phone_number=phone_number,
        status=status,
        amount_inr=99.0,
        razorpay_subscription_id=subscription.get("id"),
        razorpay_customer_id=customer_id,
        payload_json=subscription,
    )

    payment_url = subscription.get("short_url")
    if not payment_url:
        raise RuntimeError("Razorpay did not return a hosted payment page URL.")
    return str(payment_url)


async def verify_payment_webhook(payload: bytes | str, signature: str) -> dict[str, Any]:
    _ensure_webhook_config()

    payload_bytes = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature or ""):
        raise PaymentsWebhookError("Invalid Razorpay webhook signature.")

    try:
        event_data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - malformed payload should be very rare
        raise PaymentsWebhookError("Invalid Razorpay payload.") from exc

    event_type = str(event_data.get("event") or "")
    payload_wrapper = event_data.get("payload") or {}
    subscription_entity = ((payload_wrapper.get("subscription") or {}).get("entity") or {})
    payment_entity = ((payload_wrapper.get("payment") or {}).get("entity") or {})

    razorpay_subscription_id = (
        subscription_entity.get("id")
        or payment_entity.get("subscription_id")
        or ((payload_wrapper.get("subscription_renewed") or {}).get("entity") or {}).get("id")
    )
    razorpay_customer_id = subscription_entity.get("customer_id") or payment_entity.get("customer_id")
    razorpay_payment_id = payment_entity.get("id")

    subscription_row = await get_subscription_by_razorpay(
        razorpay_subscription_id=razorpay_subscription_id,
        razorpay_customer_id=razorpay_customer_id,
    )
    user_id = subscription_row.get("user_id") if subscription_row else None
    phone_number = None
    if subscription_row:
        phone_number = subscription_row.get("phone_number")

    notes = subscription_entity.get("notes") or payment_entity.get("notes") or {}
    if not user_id:
        user_id = notes.get("user_id")
    if not phone_number:
        phone_number = notes.get("phone_number")

    now = datetime.now(timezone.utc)
    updates: dict[str, Any] = {}

    if event_type == "subscription.activated":
        updates = {
            "status": "active",
            "plan": "pro",
            "started_at": _from_unix(subscription_entity.get("current_start")) or now.isoformat(),
            "expires_at": _from_unix(subscription_entity.get("current_end")) or (now + timedelta(days=30)).isoformat(),
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_customer_id": razorpay_customer_id,
        }
    elif event_type == "subscription.cancelled":
        updates = {
            "status": "expired",
            "plan": "free",
            "expires_at": now.isoformat(),
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_customer_id": razorpay_customer_id,
        }
    elif event_type == "payment.failed":
        updates = {
            "status": "payment_failed",
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_customer_id": razorpay_customer_id,
        }

    if user_id and updates:
        await upsert_subscription_for_user(str(user_id), updates)

    amount_inr = None
    if payment_entity.get("amount") is not None:
        try:
            amount_inr = round(float(payment_entity["amount"]) / 100, 2)
        except Exception:
            amount_inr = None

    await log_payment_event(
        event_type=event_type,
        user_id=str(user_id) if user_id else None,
        phone_number=str(phone_number) if phone_number else None,
        status=updates.get("status", str(subscription_entity.get("status") or payment_entity.get("status") or "received")),
        amount_inr=amount_inr,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_subscription_id=razorpay_subscription_id,
        razorpay_customer_id=razorpay_customer_id,
        payload_json=event_data,
        occurred_at=now.isoformat(),
    )

    return {
        "event_type": event_type,
        "user_id": str(user_id) if user_id else None,
        "phone_number": str(phone_number) if phone_number else None,
        "status": updates.get("status"),
        "razorpay_subscription_id": razorpay_subscription_id,
    }


async def is_pro(user_id: str) -> bool:
    return await is_user_pro(user_id)
