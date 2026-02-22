import asyncio
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from services.db import (
    get_admin_live_sessions,
    get_admin_overview_data,
    get_admin_revenue_data,
    get_admin_user_detail,
    get_admin_users_data,
    get_broadcast_targets,
    get_user_by_id,
)
from services.whatsapp import send_text

load_dotenv()

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def _verify_admin_header(authorization: str | None) -> None:
    expected = f"Bearer {ADMIN_PASSWORD}"
    if not ADMIN_PASSWORD or authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


class AdminMessageRequest(BaseModel):
    user_id: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    message: str = Field(min_length=1, max_length=1000)


class BroadcastRequest(BaseModel):
    segment: Literal["all", "pro", "free"] = "all"
    message: str = Field(min_length=1, max_length=1000)
    preview_only: bool = False


@router.get("/overview")
async def admin_overview(authorization: str | None = Header(default=None)) -> dict:
    _verify_admin_header(authorization)
    return await get_admin_overview_data()


@router.get("/users")
async def admin_users(
    authorization: str | None = Header(default=None),
    search: str = Query(default=""),
    plan: Literal["all", "free", "pro", "expired"] = "all",
    sort: Literal["joined", "last_active", "sessions"] = "joined",
) -> dict:
    _verify_admin_header(authorization)
    return await get_admin_users_data(search=search, plan_filter=plan, sort_by=sort)


@router.get("/users/{user_id}")
async def admin_user_detail(user_id: str, authorization: str | None = Header(default=None)) -> dict:
    _verify_admin_header(authorization)
    payload = await get_admin_user_detail(user_id)
    if not payload:
        raise HTTPException(status_code=404, detail="User not found.")
    return payload


@router.get("/revenue")
async def admin_revenue(authorization: str | None = Header(default=None)) -> dict:
    _verify_admin_header(authorization)
    return await get_admin_revenue_data()


@router.get("/live-sessions")
async def admin_live_sessions(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=80, ge=10, le=200),
) -> dict:
    _verify_admin_header(authorization)
    return await get_admin_live_sessions(limit=limit)


@router.post("/message")
async def admin_message_user(payload: AdminMessageRequest, authorization: str | None = Header(default=None)) -> dict:
    _verify_admin_header(authorization)

    target_phone = payload.phone_number
    if payload.user_id and not target_phone:
        user = await get_user_by_id(payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        target_phone = user.get("phone_number")

    if not target_phone:
        raise HTTPException(status_code=422, detail="phone_number or user_id is required.")

    await send_text(str(target_phone), payload.message)
    return {"status": "sent", "phone_number": str(target_phone)}


@router.post("/broadcast")
async def admin_broadcast(payload: BroadcastRequest, authorization: str | None = Header(default=None)) -> dict:
    _verify_admin_header(authorization)
    targets = await get_broadcast_targets(payload.segment)

    if payload.preview_only:
        return {"status": "preview", "target_count": len(targets)}

    sent_count = 0
    failed = []
    for phone_number in targets:
        try:
            await send_text(phone_number, payload.message)
            sent_count += 1
        except Exception:
            failed.append(phone_number)
        # Avoid WhatsApp Cloud API spikes; keep a strict 1 msg/sec cadence.
        await asyncio.sleep(1)

    return {"status": "completed", "target_count": len(targets), "sent_count": sent_count, "failed": failed}
