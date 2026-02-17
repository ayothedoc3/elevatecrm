from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.utils import now_utc
from app.pg_models.models import WorkspaceIntegration
from app.services.encryption_service import get_encryption_service


class MessagingProviderError(RuntimeError):
    pass


def _public_base_url(config: Optional[Dict[str, Any]]) -> Optional[str]:
    cfg = config or {}
    candidates = [
        cfg.get("webhook_base_url"),
        os.getenv("WEBHOOK_BASE_URL"),
        os.getenv("BACKEND_PUBLIC_URL"),
        os.getenv("APP_BASE_URL"),
    ]

    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_domain:
        candidates.append(f"https://{railway_domain}")

    for raw in candidates:
        value = (raw or "").strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value.rstrip("/")
    return None


async def _get_enabled_integration(
    db: AsyncSession,
    tenant_id: str,
    provider_type: str,
    provider_label: str,
) -> tuple[WorkspaceIntegration, str, Dict[str, Any]]:
    res = await db.execute(
        select(WorkspaceIntegration).where(
            and_(
                WorkspaceIntegration.tenant_id == tenant_id,
                WorkspaceIntegration.provider_type == provider_type,
                WorkspaceIntegration.enabled.is_(True),
            )
        )
    )
    integration = res.scalar_one_or_none()
    if not integration:
        raise MessagingProviderError(f"{provider_label} integration is not configured or is disabled")

    enc = get_encryption_service()
    try:
        secret = enc.decrypt(integration.encrypted_api_key)
    except Exception as exc:
        raise MessagingProviderError(f"Failed to decrypt {provider_label} credential") from exc

    secret = (secret or "").strip()
    if not secret:
        raise MessagingProviderError(f"{provider_label} credential is empty")

    return integration, secret, dict(integration.config or {})


def _mark_integration_used(integration: WorkspaceIntegration) -> None:
    now = now_utc()
    integration.last_used_at = now
    integration.updated_at = now


async def send_email_via_provider(
    *,
    db: AsyncSession,
    tenant_id: str,
    to_email: str,
    subject: Optional[str],
    body: str,
    body_html: Optional[str],
    message_id: str,
    campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    integration, api_key, config = await _get_enabled_integration(
        db, tenant_id, "sendgrid", "SendGrid"
    )

    from_email = (
        (config.get("from_email") or "").strip()
        or (config.get("sender_email") or "").strip()
        or (os.getenv("SENDGRID_FROM_EMAIL") or "").strip()
    )
    if not from_email:
        raise MessagingProviderError("SendGrid from_email is not configured in Settings")

    from_name = (config.get("from_name") or config.get("sender_name") or "Elev8 CRM").strip() or "Elev8 CRM"
    to_email = (to_email or "").strip()
    if not to_email:
        raise MessagingProviderError("Recipient email is required")

    custom_args = {"crm_message_id": message_id, "tenant_id": tenant_id}
    if campaign_id:
        custom_args["campaign_id"] = campaign_id

    payload: Dict[str, Any] = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": (subject or "").strip() or "Message from Elev8 CRM",
                "custom_args": custom_args,
            }
        ],
        "from": {"email": from_email, "name": from_name},
        "content": [{"type": "text/plain", "value": body or ""}],
        "tracking_settings": {
            "open_tracking": {"enable": True},
            "click_tracking": {"enable": True, "enable_text": True},
        },
    }

    if body_html:
        payload["content"].append({"type": "text/html", "value": body_html})

    timeout = httpx.Timeout(20.0, connect=8.0)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)

    if resp.status_code not in {200, 202}:
        detail = (resp.text or "").strip()
        if len(detail) > 400:
            detail = detail[:400]
        raise MessagingProviderError(f"SendGrid send failed: HTTP {resp.status_code} {detail}".strip())

    _mark_integration_used(integration)
    return {"provider": "sendgrid", "status": "sent"}


async def send_sms_via_provider(
    *,
    db: AsyncSession,
    tenant_id: str,
    to_phone: str,
    body: str,
    message_id: str,
    campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    integration, auth_token, config = await _get_enabled_integration(
        db, tenant_id, "twilio", "Twilio"
    )

    account_sid = (config.get("account_sid") or "").strip()
    from_number = (
        (config.get("from_number") or "").strip()
        or (config.get("from_phone") or "").strip()
        or (os.getenv("TWILIO_FROM_NUMBER") or "").strip()
    )

    if not account_sid:
        raise MessagingProviderError("Twilio account_sid is not configured in Settings")
    if not from_number:
        raise MessagingProviderError("Twilio from_number is not configured in Settings")

    to_phone = (to_phone or "").strip()
    if not to_phone:
        raise MessagingProviderError("Recipient phone number is required")

    payload: Dict[str, Any] = {"From": from_number, "To": to_phone, "Body": body or ""}

    callback_base = _public_base_url(config)
    if callback_base:
        params = {"message_id": message_id, "tenant_id": tenant_id}
        if campaign_id:
            params["campaign_id"] = campaign_id
        payload["StatusCallback"] = f"{callback_base}/api/webhooks/twilio/status?{urlencode(params)}"

    timeout = httpx.Timeout(20.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, auth=(account_sid, auth_token)) as client:
        resp = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data=payload,
        )

    if resp.status_code < 200 or resp.status_code >= 300:
        detail = ""
        try:
            detail = (resp.json() or {}).get("message") or ""
        except Exception:
            detail = (resp.text or "").strip()
        if len(detail) > 400:
            detail = detail[:400]
        raise MessagingProviderError(f"Twilio send failed: HTTP {resp.status_code} {detail}".strip())

    response_data: Dict[str, Any] = {}
    try:
        response_data = resp.json() or {}
    except Exception:
        response_data = {}

    provider_status = str(response_data.get("status") or "").strip().lower()
    crm_status = "sent" if provider_status in {"queued", "accepted", "sending", "sent"} else "pending"

    _mark_integration_used(integration)
    return {
        "provider": "twilio",
        "status": crm_status,
        "external_status": provider_status or None,
        "external_id": response_data.get("sid"),
    }


async def send_outbound_message_via_provider(
    *,
    db: AsyncSession,
    tenant_id: str,
    channel: str,
    to_address: str,
    subject: Optional[str],
    body: str,
    body_html: Optional[str],
    message_id: str,
    campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    channel_norm = (channel or "").strip().lower()
    if channel_norm == "email":
        return await send_email_via_provider(
            db=db,
            tenant_id=tenant_id,
            to_email=to_address,
            subject=subject,
            body=body,
            body_html=body_html,
            message_id=message_id,
            campaign_id=campaign_id,
        )
    if channel_norm == "sms":
        return await send_sms_via_provider(
            db=db,
            tenant_id=tenant_id,
            to_phone=to_address,
            body=body,
            message_id=message_id,
            campaign_id=campaign_id,
        )
    raise MessagingProviderError(f"Unsupported channel: {channel}")

