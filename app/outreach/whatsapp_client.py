import base64
import re
import uuid
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class WhatsAppServiceError(RuntimeError):
    def __init__(self, code: str, status_code: int = 503) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def normalize_phone(value: str) -> str:
    raw = value.strip()
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    normalized = "+" + re.sub(r"\D", "", raw)
    if not _E164.fullmatch(normalized):
        raise ValueError("WhatsApp number must be in international E.164 format.")
    return normalized


def clinic_account_id(clinic_id: uuid.UUID) -> str:
    return f"clinic_{uuid.UUID(str(clinic_id)).hex}"


@dataclass
class WhatsAppServiceClient:
    base_url: str | None = None
    token: str | None = None

    def __post_init__(self) -> None:
        settings = get_settings()
        self.base_url = (self.base_url or settings.whatsapp_service_url or "").rstrip("/")
        self.token = self.token if self.token is not None else settings.whatsapp_service_token

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self.base_url:
            raise WhatsAppServiceError("WHATSAPP_SERVICE_NOT_CONFIGURED")
        headers = dict(kwargs.pop("headers", {}))
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with httpx.AsyncClient(timeout=get_settings().whatsapp_service_timeout_seconds) as client:
                response = await client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise WhatsAppServiceError("WHATSAPP_SERVICE_TIMEOUT") from exc
        except httpx.TransportError as exc:
            raise WhatsAppServiceError("WHATSAPP_SERVICE_UNAVAILABLE") from exc
        if response.status_code >= 400:
            try:
                code = str(response.json().get("error") or "WHATSAPP_SERVICE_ERROR")
            except ValueError:
                code = "WHATSAPP_SERVICE_ERROR"
            raise WhatsAppServiceError(code.upper(), response.status_code)
        return response.json()

    async def status(self, clinic_id: uuid.UUID) -> dict:
        return await self._request("GET", "/whatsapp/status", params={"account_id": clinic_account_id(clinic_id)})

    async def qr(self, clinic_id: uuid.UUID) -> dict:
        return await self._request("GET", "/whatsapp/qr", params={"account_id": clinic_account_id(clinic_id)})

    async def logout(self, clinic_id: uuid.UUID) -> dict:
        return await self._request("POST", "/whatsapp/logout", json={"account_id": clinic_account_id(clinic_id)})

    async def validate_phone(self, clinic_id: uuid.UUID, phone: str) -> dict:
        return await self._request("GET", "/whatsapp/validate", params={"account_id": clinic_account_id(clinic_id), "phone": normalize_phone(phone)})

    async def send_message(self, clinic_id: uuid.UUID, phone: str, message: str) -> dict:
        return await self._request("POST", "/whatsapp/send", json={"account_id": clinic_account_id(clinic_id), "phone": normalize_phone(phone), "message": message})

    async def send_image_message(self, clinic_id: uuid.UUID, phone: str, message: str, image: bytes, mime_type: str = "image/jpeg") -> dict:
        return await self._request("POST", "/whatsapp/send", json={
            "account_id": clinic_account_id(clinic_id), "phone": normalize_phone(phone), "message": message,
            "image_base64": base64.b64encode(image).decode(), "image_mime_type": mime_type,
        })
