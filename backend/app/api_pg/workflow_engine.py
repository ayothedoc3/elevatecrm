from __future__ import annotations

import asyncio
import json
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional
from urllib import error as url_error
from urllib import request as url_request

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.messaging_service import MessagingProviderError, send_outbound_message_via_provider
from app.api_pg.services import create_timeline_event
from app.api_pg.utils import now_utc
from app.core.database import AsyncSessionLocal
from app.pg_models.models import (
    Affiliate,
    AffiliateCommission,
    AffiliateNotification,
    AffiliateProgram,
    Contact,
    Conversation,
    Deal,
    Message,
    Pipeline,
    PipelineStage,
    Task,
    User,
    Workflow,
    WorkflowRun,
)

_scheduled_tasks: set[asyncio.Task] = set()


def _track_task(task: asyncio.Task) -> None:
    _scheduled_tasks.add(task)
    task.add_done_callback(lambda t: _scheduled_tasks.discard(t))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _render_template(text: Optional[str], values: Dict[str, Any]) -> str:
    rendered = _as_text(text)
    for key, value in (values or {}).items():
        rendered = rendered.replace(f"{{{{{key}}}}}", _as_text(value))
    return rendered


def _action_config(action: Dict[str, Any]) -> Dict[str, Any]:
    config = dict(action.get("config") or {})
    for key, value in (action or {}).items():
        if key in {"type", "config"}:
            continue
        if key not in config and key in action:
            config[key] = value
    return config


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _to_number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _evaluate_condition(config: Dict[str, Any], values: Dict[str, Any]) -> bool:
    field = (config.get("field") or config.get("left") or "").strip()
    operator = (config.get("operator") or "eq").strip().lower()
    expected = config.get("value")
    if expected is None and "right" in config:
        expected = config.get("right")
    if isinstance(expected, str):
        expected = _render_template(expected, values)

    actual = values.get(field) if field else None
    if isinstance(actual, str):
        actual = actual.strip()

    if operator in {"exists", "is_set"}:
        return actual is not None and str(actual).strip() != ""
    if operator in {"not_exists", "is_not_set"}:
        return actual is None or str(actual).strip() == ""
    if operator in {"truthy"}:
        return _is_truthy(actual)
    if operator in {"falsy"}:
        return not _is_truthy(actual)

    if operator in {"in", "not_in"}:
        expected_values = expected
        if isinstance(expected_values, str):
            expected_values = [part.strip() for part in expected_values.split(",") if part.strip()]
        if not isinstance(expected_values, (list, tuple, set)):
            expected_values = [expected_values]
        contains = str(actual) in {str(v) for v in expected_values}
        return contains if operator == "in" else not contains

    if operator in {"gt", "gte", "lt", "lte"}:
        actual_num = _to_number(actual)
        expected_num = _to_number(expected)
        if actual_num is None or expected_num is None:
            return False
        if operator == "gt":
            return actual_num > expected_num
        if operator == "gte":
            return actual_num >= expected_num
        if operator == "lt":
            return actual_num < expected_num
        return actual_num <= expected_num

    actual_text = str(actual).strip().lower() if actual is not None else ""
    expected_text = str(expected).strip().lower() if expected is not None else ""
    if operator in {"contains"}:
        return expected_text in actual_text
    if operator in {"starts_with"}:
        return actual_text.startswith(expected_text)
    if operator in {"ends_with"}:
        return actual_text.endswith(expected_text)
    if operator in {"ne", "not_eq"}:
        return actual_text != expected_text
    return actual_text == expected_text


def _trigger_matches(workflow: Workflow, trigger_data: Dict[str, Any]) -> bool:
    cfg = dict(workflow.trigger_config or {})
    if not cfg:
        return True
    data = trigger_data or {}
    for key, expected in cfg.items():
        if expected is None or expected == "":
            continue
        actual = data.get(key)
        if str(actual).strip().lower() != str(expected).strip().lower():
            return False
    return True


async def _get_or_create_conversation(
    *,
    db: AsyncSession,
    tenant_id: str,
    contact_id: str,
    channel: str,
    subject: Optional[str],
) -> Conversation:
    conv_res = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.contact_id == contact_id,
                Conversation.channel == channel,
            )
        )
    )
    conv = conv_res.scalar_one_or_none()
    if conv:
        return conv

    now = now_utc()
    conv = Conversation(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=channel,
        subject=subject,
        is_open=True,
        is_read=True,
        message_count=0,
        unread_count=0,
        last_message_preview=None,
        last_message_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    await db.flush()
    return conv


async def _load_contact(db: AsyncSession, tenant_id: str, contact_id: Optional[str]) -> Optional[Contact]:
    if not contact_id:
        return None
    res = await db.execute(select(Contact).where(and_(Contact.id == contact_id, Contact.tenant_id == tenant_id)))
    return res.scalar_one_or_none()


async def _load_deal(db: AsyncSession, tenant_id: str, deal_id: Optional[str]) -> Optional[Deal]:
    if not deal_id:
        return None
    res = await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))
    return res.scalar_one_or_none()


def _template_values(contact: Optional[Contact], deal: Optional[Deal], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = dict(trigger_data or {})
    if contact:
        values.update(
            {
                "contact_id": contact.id,
                "first_name": contact.first_name or "",
                "last_name": contact.last_name or "",
                "full_name": contact.full_name or "",
                "email": contact.email or "",
                "phone": contact.phone or "",
                "company_name": contact.company_name or "",
            }
        )
    if deal:
        values.update(
            {
                "deal_id": deal.id,
                "deal_name": deal.name or "",
                "deal_amount": float(deal.amount or 0),
                "deal_stage_id": deal.stage_id or "",
                "deal_status": deal.status or "",
            }
        )
    return values


async def _execute_send_message_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    action_type: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    channel = "sms" if action_type == "send_sms" else "email"
    to_address = _render_template(config.get("to") or config.get("to_address"), values).strip()
    if not to_address and contact:
        to_address = (contact.phone or "").strip() if channel == "sms" else (contact.email or "").strip()
    if not to_address:
        to_address = _render_template(values.get("phone") if channel == "sms" else values.get("email"), values).strip()
    if not to_address:
        raise RuntimeError(f"Workflow action '{action_type}' has no recipient")

    subject = _render_template(config.get("subject") or "Message from Elev8 CRM", values) if channel == "email" else None
    body = _render_template(config.get("body") or config.get("template") or "", values)
    if not body.strip():
        raise RuntimeError(f"Workflow action '{action_type}' has empty body")

    conversation: Optional[Conversation] = None
    if contact:
        conversation = await _get_or_create_conversation(
            db=db,
            tenant_id=tenant_id,
            contact_id=contact.id,
            channel=channel,
            subject=subject,
        )

    now = now_utc()
    message = Message(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        conversation_id=conversation.id if conversation else str(uuid.uuid4()),
        channel=channel,
        direction="outbound",
        status="pending",
        from_address=None,
        to_address=to_address,
        subject=subject,
        body=body,
        body_html=None,
        sent_by_user_id=None,
        sent_by_name="Automation",
        sent_at=now,
        created_at=now,
    )

    if conversation is None:
        synthetic = Conversation(
            id=message.conversation_id,
            tenant_id=tenant_id,
            contact_id=contact.id if contact else None,
            channel=channel,
            subject=subject,
            is_open=True,
            is_read=True,
            message_count=0,
            unread_count=0,
            last_message_preview=None,
            last_message_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add(synthetic)
        conversation = synthetic

    db.add(message)

    try:
        result = await send_outbound_message_via_provider(
            db=db,
            tenant_id=tenant_id,
            channel=channel,
            to_address=to_address,
            subject=subject,
            body=body,
            body_html=None,
            message_id=message.id,
            campaign_id=None,
        )
        message.status = result.get("status") or "sent"
    except MessagingProviderError:
        message.status = "failed"

    preview = body[:100] + ("..." if len(body) > 100 else "")
    conversation.message_count = int(conversation.message_count or 0) + 1
    conversation.last_message_preview = preview
    conversation.last_message_at = now
    conversation.updated_at = now
    conversation.is_read = True
    conversation.unread_count = 0

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="sms_sent" if channel == "sms" else "email_sent",
        title="Workflow sent SMS" if channel == "sms" else "Workflow sent email",
        description=body[:500],
        deal_id=deal.id if deal else None,
        contact_id=contact.id if contact else None,
        metadata={"workflow": True, "message_id": message.id, "channel": channel},
    )


async def _execute_create_task_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    title = _render_template(config.get("title") or "Workflow task", values).strip() or "Workflow task"
    description = _render_template(config.get("description"), values).strip() or None
    due_days = _safe_int(config.get("due_days"), 0)
    due_hours = _safe_int(config.get("due_hours"), 0)
    if due_days <= 0 and due_hours <= 0:
        due_hours = 24

    due_at = now_utc() + timedelta(days=max(0, due_days), hours=max(0, due_hours))
    owner_id = (config.get("owner_id") or "").strip() or (deal.owner_id if deal else None) or (contact.owner_id if contact else None)
    related_type = "deal" if deal else ("contact" if contact else None)
    related_id = deal.id if deal else (contact.id if contact else None)

    task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=title,
        description=description,
        due_at=due_at,
        owner_id=owner_id,
        created_by=None,
        status="open",
        kind="manual",
        related_type=related_type,
        related_id=related_id,
        completed_at=None,
        completed_by=None,
        meta={"workflow": True},
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(task)


async def _execute_add_tag_action(
    *,
    db: AsyncSession,
    config: Dict[str, Any],
    contact: Optional[Contact],
    values: Dict[str, Any],
) -> None:
    if not contact:
        return
    tag = _render_template(config.get("tag"), values).strip()
    if not tag:
        return
    tags = list(contact.tags or [])
    if tag not in tags:
        tags.append(tag)
        contact.tags = tags
        contact.updated_at = now_utc()
        await db.flush()


async def _execute_remove_tag_action(
    *,
    db: AsyncSession,
    config: Dict[str, Any],
    contact: Optional[Contact],
    values: Dict[str, Any],
) -> None:
    if not contact:
        return
    tag = _render_template(config.get("tag"), values).strip()
    if not tag:
        return
    tags = [item for item in list(contact.tags or []) if str(item).strip() != tag]
    if len(tags) != len(list(contact.tags or [])):
        contact.tags = tags
        contact.updated_at = now_utc()
        await db.flush()


async def _resolve_valid_owner_id(
    *,
    db: AsyncSession,
    tenant_id: str,
    owner_id: Optional[str],
) -> Optional[str]:
    candidate = (owner_id or "").strip() or None
    if not candidate:
        return None
    owner = (
        await db.execute(
            select(User).where(
                and_(
                    User.id == candidate,
                    User.tenant_id == tenant_id,
                    User.is_active.is_(True),
                )
            )
        )
    ).scalar_one_or_none()
    return owner.id if owner else None


async def _execute_assign_owner_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    raw_owner_id = _render_template(config.get("owner_id"), values).strip() if config.get("owner_id") else None
    owner_id = await _resolve_valid_owner_id(db=db, tenant_id=tenant_id, owner_id=raw_owner_id)
    if not owner_id:
        return

    object_type = (config.get("object_type") or "").strip().lower()
    if not object_type:
        object_type = "deal" if deal else "contact"

    now = now_utc()
    if object_type == "deal" and deal:
        deal.owner_id = owner_id
        deal.updated_at = now
        return
    if object_type in {"contact", "lead"} and contact:
        contact.owner_id = owner_id
        contact.updated_at = now


async def _execute_move_deal_stage_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    if not deal:
        return
    target_stage_id = _render_template(config.get("stage_id") or config.get("to_stage_id"), values).strip()
    if not target_stage_id:
        return

    stage = (
        await db.execute(
            select(PipelineStage)
            .join(Pipeline, Pipeline.id == PipelineStage.pipeline_id)
            .where(
                and_(
                    PipelineStage.id == target_stage_id,
                    Pipeline.tenant_id == tenant_id,
                )
            )
        )
    ).scalar_one_or_none()
    if not stage:
        return

    now = now_utc()
    old_stage_id = deal.stage_id
    deal.stage_id = stage.id
    status_override = (config.get("status") or "").strip().lower()
    if status_override in {"open", "won", "lost"}:
        deal.status = status_override
    deal.updated_at = now

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="stage_changed",
        title="Workflow moved deal stage",
        deal_id=deal.id,
        contact_id=deal.contact_id,
        metadata={"from_stage_id": old_stage_id, "to_stage_id": stage.id, "workflow": True},
    )


async def _default_pipeline_and_stage(
    *,
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: Optional[str],
    stage_id: Optional[str],
) -> tuple[Optional[Pipeline], Optional[PipelineStage]]:
    selected_pipeline: Optional[Pipeline] = None
    selected_stage: Optional[PipelineStage] = None

    if pipeline_id:
        selected_pipeline = (
            await db.execute(
                select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id))
            )
        ).scalar_one_or_none()
    if not selected_pipeline:
        selected_pipeline = (
            await db.execute(
                select(Pipeline)
                .where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)))
                .order_by(Pipeline.display_order.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if not selected_pipeline:
        selected_pipeline = (
            await db.execute(
                select(Pipeline)
                .where(Pipeline.tenant_id == tenant_id)
                .order_by(Pipeline.display_order.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

    if selected_pipeline and stage_id:
        selected_stage = (
            await db.execute(
                select(PipelineStage).where(
                    and_(
                        PipelineStage.id == stage_id,
                        PipelineStage.pipeline_id == selected_pipeline.id,
                    )
                )
            )
        ).scalar_one_or_none()
    if selected_pipeline and not selected_stage:
        selected_stage = (
            await db.execute(
                select(PipelineStage)
                .where(PipelineStage.pipeline_id == selected_pipeline.id)
                .order_by(PipelineStage.display_order.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

    return selected_pipeline, selected_stage


async def _execute_create_deal_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> Optional[Deal]:
    if deal and bool(config.get("skip_if_deal_exists", True)):
        return deal
    if not contact:
        return deal
    if not contact.converted_from_lead_id:
        return deal
    if not contact.account_id:
        return deal

    requested_pipeline_id = _render_template(config.get("pipeline_id"), values).strip() if config.get("pipeline_id") else None
    requested_stage_id = _render_template(config.get("stage_id"), values).strip() if config.get("stage_id") else None
    pipeline, stage = await _default_pipeline_and_stage(
        db=db,
        tenant_id=tenant_id,
        pipeline_id=requested_pipeline_id,
        stage_id=requested_stage_id,
    )
    if not pipeline or not stage:
        return deal

    name = _render_template(config.get("name") or "{{company_name}} Opportunity", values).strip()
    if not name:
        name = f"{contact.company_name or contact.full_name or contact.id} Opportunity"
    amount = max(0.0, _safe_float(_render_template(config.get("amount"), values) if config.get("amount") is not None else 0.0, 0.0))
    close_days = max(1, _safe_int(config.get("estimated_close_in_days"), 30))
    product_service_type = _render_template(config.get("product_service_type") or "Workflow-generated opportunity", values).strip()
    now = now_utc()
    new_deal = Deal(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        amount=amount,
        currency="USD",
        status="open",
        origin_lead_id=contact.converted_from_lead_id,
        contact_id=contact.id,
        account_id=contact.account_id,
        account_name=contact.account_name or contact.company_name,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        next_step_at=now + timedelta(days=max(1, _safe_int(config.get("next_step_in_days"), 1))),
        next_step_note=_render_template(config.get("next_step_note") or "Workflow follow-up", values).strip(),
        estimated_close_date=now + timedelta(days=close_days),
        product_service_type=product_service_type,
        lead_score=int(contact.lead_score or 0),
        lead_tier=(contact.lead_tier or "D").strip().upper(),
        sales_motion_type="partnership_sales",
        owner_id=contact.owner_id,
        last_override={},
        handoff_status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(new_deal)
    await db.flush()
    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="deal_created",
        title=f"Workflow created deal: {new_deal.name}",
        deal_id=new_deal.id,
        contact_id=contact.id,
        metadata={"workflow": True},
    )
    return new_deal


async def _execute_request_document_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    title = _render_template(config.get("title") or "Document request", values).strip() or "Document request"
    description = _render_template(
        config.get("description") or config.get("body") or "Please provide the requested document(s).",
        values,
    ).strip()
    due_days = max(1, _safe_int(config.get("due_days"), 3))
    owner_id = (config.get("owner_id") or "").strip() or (deal.owner_id if deal else None) or (contact.owner_id if contact else None)
    related_type = "deal" if deal else ("contact" if contact else None)
    related_id = deal.id if deal else (contact.id if contact else None)
    now = now_utc()
    task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=title,
        description=description or None,
        due_at=now + timedelta(days=due_days),
        owner_id=owner_id,
        created_by=None,
        status="open",
        kind="document_request",
        related_type=related_type,
        related_id=related_id,
        completed_at=None,
        completed_by=None,
        meta={"workflow": True},
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="document_requested",
        title=title,
        description=description or None,
        deal_id=deal.id if deal else None,
        contact_id=contact.id if contact else None,
        metadata={"workflow": True, "task_id": task.id},
    )


def _render_json_payload(payload: Any, values: Dict[str, Any]) -> Any:
    if isinstance(payload, dict):
        return {k: _render_json_payload(v, values) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_render_json_payload(item, values) for item in payload]
    if isinstance(payload, str):
        return _render_template(payload, values)
    return payload


async def _execute_fire_webhook_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    url = _render_template(config.get("url") or config.get("webhook_url"), values).strip()
    if not url:
        return

    method = (_render_template(config.get("method") or "POST", values).strip() or "POST").upper()
    timeout_seconds = max(1, _safe_int(config.get("timeout_seconds"), 10))
    headers = dict(config.get("headers") or {})
    headers.setdefault("Content-Type", "application/json")
    payload = config.get("payload", config.get("body", {}))
    rendered_payload = _render_json_payload(payload, values)

    if isinstance(rendered_payload, (dict, list)):
        data_bytes = json.dumps(rendered_payload).encode("utf-8")
    elif rendered_payload is None:
        data_bytes = b""
    else:
        data_bytes = str(rendered_payload).encode("utf-8")

    def _send_webhook():
        req = url_request.Request(url=url, data=data_bytes if method != "GET" else None, method=method)
        for header_key, header_value in headers.items():
            req.add_header(str(header_key), str(header_value))
        with url_request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            return int(response.status), body

    status_code = None
    response_preview = None
    try:
        status_code, response_preview = await asyncio.to_thread(_send_webhook)
    except (url_error.URLError, ValueError):
        status_code = None
        response_preview = None

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="webhook_fired",
        title="Workflow fired webhook",
        description=f"{method} {url}",
        deal_id=deal.id if deal else None,
        contact_id=contact.id if contact else None,
        metadata={
            "workflow": True,
            "url": url,
            "method": method,
            "status_code": status_code,
            "response_preview": response_preview,
        },
    )


def _affiliate_id_from_context(config: Dict[str, Any], values: Dict[str, Any]) -> Optional[str]:
    return (_render_template(config.get("affiliate_id"), values).strip() if config.get("affiliate_id") else None) or (
        str(values.get("affiliate_id") or "").strip() or None
    )


def _program_id_from_context(config: Dict[str, Any], values: Dict[str, Any]) -> Optional[str]:
    return (_render_template(config.get("program_id"), values).strip() if config.get("program_id") else None) or (
        str(values.get("program_id") or "").strip() or None
    )


async def _execute_affiliate_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    action_type: str,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    affiliate_id = _affiliate_id_from_context(config, values)
    program_id = _program_id_from_context(config, values)
    if not affiliate_id:
        return

    affiliate = (
        await db.execute(
            select(Affiliate).where(and_(Affiliate.id == affiliate_id, Affiliate.tenant_id == tenant_id))
        )
    ).scalar_one_or_none()
    if not affiliate:
        return

    now = now_utc()
    if action_type == "approve_affiliate":
        affiliate.status = "approved"
        affiliate.updated_at = now
        return

    if action_type == "update_affiliate_status":
        next_status = _render_template(config.get("status") or "", values).strip().lower()
        if next_status:
            affiliate.status = next_status
            affiliate.updated_at = now
        return

    if action_type == "notify_affiliate":
        title = _render_template(config.get("title") or "Affiliate notification", values).strip() or "Affiliate notification"
        message = _render_template(config.get("message") or config.get("body") or "", values).strip()
        if not message:
            return
        notification = AffiliateNotification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            affiliate_id=affiliate.id,
            notification_type="workflow",
            title=title,
            message=message,
            is_read=False,
            meta={"workflow": True},
            created_at=now,
            read_at=None,
        )
        db.add(notification)
        return

    if action_type == "create_commission":
        if not program_id:
            return
        program = (
            await db.execute(
                select(AffiliateProgram).where(
                    and_(AffiliateProgram.id == program_id, AffiliateProgram.tenant_id == tenant_id)
                )
            )
        ).scalar_one_or_none()
        if not program:
            return

        amount = _safe_float(_render_template(config.get("amount"), values) if config.get("amount") is not None else None, None)
        if amount is None:
            if deal and float(deal.amount or 0) > 0:
                if (program.commission_type or "").strip().lower() == "percentage":
                    amount = float(deal.amount or 0.0) * (float(program.commission_value or 0.0) / 100.0)
                else:
                    amount = float(program.commission_value or 0.0)
            else:
                amount = 0.0
        amount = max(0.0, float(amount or 0.0))

        commission = AffiliateCommission(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            affiliate_id=affiliate.id,
            program_id=program.id,
            deal_id=deal.id if deal else None,
            payment_id=None,
            amount=amount,
            currency=(config.get("currency") or "USD"),
            status=(config.get("status") or "pending"),
            notes=_render_template(config.get("notes"), values).strip() or None,
            approved_at=None,
            approved_by=None,
            paid_at=None,
            paid_by=None,
            created_at=now,
            updated_at=now,
        )
        db.add(commission)
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="commission_created",
            title="Workflow created affiliate commission",
            deal_id=deal.id if deal else None,
            contact_id=contact.id if contact else None,
            metadata={"workflow": True, "affiliate_id": affiliate.id, "program_id": program.id, "amount": amount},
        )


async def _execute_set_property_action(
    *,
    db: AsyncSession,
    config: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    values: Dict[str, Any],
) -> None:
    prop = (config.get("property") or "").strip()
    if not prop:
        return
    val = _render_template(config.get("value"), values)
    object_type = (config.get("object_type") or "contact").strip().lower()

    if object_type == "deal" and deal:
        allowed = {"status", "next_step_note", "lead_score", "lead_tier"}
        if prop in allowed:
            setattr(deal, prop, val)
            deal.updated_at = now_utc()
        return

    if contact:
        allowed = {"lifecycle_stage", "lead_score", "lead_tier", "status", "company_name", "phone", "email"}
        if prop in allowed:
            if prop == "lead_score":
                setattr(contact, prop, _safe_int(val, contact.lead_score or 0))
            else:
                setattr(contact, prop, val)
            contact.updated_at = now_utc()


async def _execute_action(
    *,
    db: AsyncSession,
    tenant_id: str,
    action: Dict[str, Any],
    contact: Optional[Contact],
    deal: Optional[Deal],
    trigger_data: Dict[str, Any],
) -> Optional[Deal]:
    action_type = (action.get("type") or "").strip().lower()
    config = _action_config(action)
    values = _template_values(contact, deal, trigger_data)

    if action_type in {"send_email", "send_sms"}:
        await _execute_send_message_action(
            db=db,
            tenant_id=tenant_id,
            action_type=action_type,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    if action_type == "create_task":
        await _execute_create_task_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    if action_type == "add_tag":
        await _execute_add_tag_action(db=db, config=config, contact=contact, values=values)
        return deal

    if action_type == "remove_tag":
        await _execute_remove_tag_action(db=db, config=config, contact=contact, values=values)
        return deal

    if action_type == "assign_owner":
        await _execute_assign_owner_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    if action_type == "move_deal_stage":
        await _execute_move_deal_stage_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            deal=deal,
            values=values,
        )
        return deal

    if action_type == "create_deal":
        return await _execute_create_deal_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )

    if action_type == "request_document":
        await _execute_request_document_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    if action_type == "set_property":
        await _execute_set_property_action(db=db, config=config, contact=contact, deal=deal, values=values)
        return deal

    if action_type == "create_notification":
        title = _render_template(config.get("title") or "Workflow notification", values)
        description = _render_template(config.get("description"), values) or None
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="internal_notification",
            title=title,
            description=description,
            deal_id=deal.id if deal else None,
            contact_id=contact.id if contact else None,
            metadata={"workflow": True},
        )
        return deal

    if action_type == "fire_webhook":
        await _execute_fire_webhook_action(
            db=db,
            tenant_id=tenant_id,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    if action_type in {"approve_affiliate", "create_commission", "notify_affiliate", "update_affiliate_status"}:
        await _execute_affiliate_action(
            db=db,
            tenant_id=tenant_id,
            action_type=action_type,
            config=config,
            contact=contact,
            deal=deal,
            values=values,
        )
        return deal

    return deal


async def _resume_after_delay(
    *,
    tenant_id: str,
    workflow_id: str,
    run_id: str,
    contact_id: Optional[str],
    deal_id: Optional[str],
    trigger_data: Dict[str, Any],
    next_index: int,
    delay_minutes: int,
) -> None:
    await asyncio.sleep(max(0, delay_minutes) * 60)
    async with AsyncSessionLocal() as db:
        workflow = (
            await db.execute(
                select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id))
            )
        ).scalar_one_or_none()
        run = (
            await db.execute(
                select(WorkflowRun).where(and_(WorkflowRun.id == run_id, WorkflowRun.tenant_id == tenant_id))
            )
        ).scalar_one_or_none()

        if not workflow or not run:
            return
        if run.status in {"completed", "failed"}:
            return

        try:
            await _execute_workflow_run(
                db=db,
                workflow=workflow,
                run=run,
                trigger_data=trigger_data,
                contact_id=contact_id,
                deal_id=deal_id,
                start_index=next_index,
            )
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = now_utc()
            workflow.failed_runs = int(workflow.failed_runs or 0) + 1
            await db.flush()
        await db.commit()


async def _execute_workflow_run(
    *,
    db: AsyncSession,
    workflow: Workflow,
    run: WorkflowRun,
    trigger_data: Dict[str, Any],
    contact_id: Optional[str],
    deal_id: Optional[str],
    start_index: int = 0,
) -> None:
    try:
        actions = list(workflow.actions or [])
    except Exception:
        actions = []

    contact = await _load_contact(db, workflow.tenant_id, contact_id)
    deal = await _load_deal(db, workflow.tenant_id, deal_id)

    index = max(0, start_index)
    while index < len(actions):
        action = dict(actions[index] or {})
        action_type = (action.get("type") or "").strip().lower()
        delay_minutes = _safe_int(action.get("delay_minutes"), 0)
        config = _action_config(action)

        if action_type == "delay":
            delay_minutes = max(1, delay_minutes)
            run.status = "waiting"
            run.error = None
            await db.flush()
            task = asyncio.create_task(
                _resume_after_delay(
                    tenant_id=workflow.tenant_id,
                    workflow_id=workflow.id,
                    run_id=run.id,
                    contact_id=contact_id,
                    deal_id=deal_id,
                    trigger_data=trigger_data,
                    next_index=index + 1,
                    delay_minutes=delay_minutes,
                )
            )
            _track_task(task)
            return

        if action_type == "if_condition":
            values = _template_values(contact, deal, trigger_data)
            condition_met = _evaluate_condition(config, values)
            if not condition_met:
                on_false = (config.get("on_false") or "skip").strip().lower()
                if on_false == "stop":
                    break
                skip_actions = max(1, _safe_int(config.get("skip_actions"), 1))
                index += 1 + skip_actions
                continue
            index += 1
            continue

        if delay_minutes > 0:
            run.status = "waiting"
            run.error = None
            await db.flush()
            task = asyncio.create_task(
                _resume_after_delay(
                    tenant_id=workflow.tenant_id,
                    workflow_id=workflow.id,
                    run_id=run.id,
                    contact_id=contact_id,
                    deal_id=deal_id,
                    trigger_data=trigger_data,
                    next_index=index,
                    delay_minutes=delay_minutes,
                )
            )
            _track_task(task)
            return

        deal = await _execute_action(
            db=db,
            tenant_id=workflow.tenant_id,
            action=action,
            contact=contact,
            deal=deal,
            trigger_data=trigger_data,
        )
        index += 1

    run.status = "completed"
    run.completed_at = now_utc()
    run.error = None
    workflow.successful_runs = int(workflow.successful_runs or 0) + 1
    await db.flush()


async def trigger_workflow_by_id(
    *,
    db: AsyncSession,
    tenant_id: str,
    workflow_id: str,
    trigger_type: str,
    trigger_data: Optional[Dict[str, Any]] = None,
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
) -> Optional[WorkflowRun]:
    res = await db.execute(
        select(Workflow).where(
            and_(
                Workflow.id == workflow_id,
                Workflow.tenant_id == tenant_id,
                Workflow.status == "active",
            )
        )
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        return None

    run = WorkflowRun(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        status="running",
        trigger_type=trigger_type,
        trigger_data=trigger_data or {},
        contact_id=contact_id,
        deal_id=deal_id,
        error=None,
        started_at=now_utc(),
        completed_at=None,
    )
    db.add(run)

    workflow.total_runs = int(workflow.total_runs or 0) + 1
    await db.flush()

    try:
        await _execute_workflow_run(
            db=db,
            workflow=workflow,
            run=run,
            trigger_data=trigger_data or {},
            contact_id=contact_id,
            deal_id=deal_id,
            start_index=0,
        )
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = now_utc()
        workflow.failed_runs = int(workflow.failed_runs or 0) + 1
        await db.flush()

    return run


async def trigger_workflows_for_event(
    *,
    db: AsyncSession,
    tenant_id: str,
    trigger_type: str,
    trigger_data: Optional[Dict[str, Any]] = None,
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
) -> List[WorkflowRun]:
    data = trigger_data or {}
    workflows_res = await db.execute(
        select(Workflow).where(
            and_(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "active",
                Workflow.trigger_type == trigger_type,
            )
        )
    )
    workflows = workflows_res.scalars().all()
    runs: List[WorkflowRun] = []
    for workflow in workflows:
        if not _trigger_matches(workflow, data):
            continue
        run = await trigger_workflow_by_id(
            db=db,
            tenant_id=tenant_id,
            workflow_id=workflow.id,
            trigger_type=trigger_type,
            trigger_data=data,
            contact_id=contact_id,
            deal_id=deal_id,
        )
        if run:
            runs.append(run)
    return runs
