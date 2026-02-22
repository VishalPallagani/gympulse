import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppConfigError(RuntimeError):
    pass


def _ensure_config() -> None:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise WhatsAppConfigError(
            "WhatsApp Cloud API is not configured. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID."
        )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}


async def send_text(phone_number: str, message: str) -> None:
    _ensure_config()

    url = f"{GRAPH_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=_headers(), json=payload)

    if response.status_code >= 400:
        logger.error("WhatsApp send_text failed (%s): %s", response.status_code, response.text)
        raise RuntimeError("Failed to send WhatsApp text message.")


async def send_image(phone_number: str, image_path: str) -> None:
    _ensure_config()

    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    upload_url = f"{GRAPH_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/media"
    send_url = f"{GRAPH_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    async with httpx.AsyncClient(timeout=60) as client:
        with image_file.open("rb") as file_handle:
            upload_response = await client.post(
                upload_url,
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                data={"messaging_product": "whatsapp"},
                files={"file": (image_file.name, file_handle, "image/png")},
            )

        if upload_response.status_code >= 400:
            logger.error("WhatsApp media upload failed (%s): %s", upload_response.status_code, upload_response.text)
            raise RuntimeError("Failed to upload image to WhatsApp.")

        media_id = upload_response.json().get("id")
        if not media_id:
            logger.error("WhatsApp media upload did not return media id: %s", upload_response.text)
            raise RuntimeError("Failed to upload image to WhatsApp.")

        message_payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "image",
            "image": {"id": media_id},
        }
        message_response = await client.post(send_url, headers=_headers(), json=message_payload)

    if message_response.status_code >= 400:
        logger.error("WhatsApp send_image failed (%s): %s", message_response.status_code, message_response.text)
        raise RuntimeError("Failed to send WhatsApp image message.")
