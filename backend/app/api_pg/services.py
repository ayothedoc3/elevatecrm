from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.utils import now_utc, normalize_lower, scoring_inputs_complete
from app.pg_models.models import (
    Account,
    CalculationDefinition,
    CalculationResult,
    Deal,
    DealHandoff,
    Lead,
    Partner,
    Pipeline,
    PipelineStage,
    Product,
    Task,
    TimelineEvent,
    User,
    WorkspaceIntegration,
    WorkspaceSetting,
)
from app.services.encryption_service import get_encryption_service

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

DEFAULT_SLA_CONFIG: Dict[str, int] = {
    "speed_to_lead_minutes": 15,
    "lead_cadence_hours": 24,
    "deal_cadence_hours": 72,
}

LEAD_ACTIVE_STATUSES = {"new", "assigned", "new_assigned", "working", "info_collected", "qualified", "unresponsive", "nurture"}

LEAD_SLA_TASK_KIND = "lead_sla"
DEAL_RISK_TASK_KIND = "deal_risk"
KICKOFF_TASK_KIND = "kickoff"

FINANCE_ROLES = {"finance"}
MANAGER_ROLES = {"manager", "admin", "owner", "super_admin"}

TOUCHPOINT_EVENT_TYPES = {
    "call_log",
    "email_sent",
    "email_received",
    "sms_sent",
    "sms_received",
    "meeting",
}

MENTION_RE = re.compile(r"(?:(?<=\\s)|^)@([A-Za-z0-9][A-Za-z0-9_.-]{1,63})")


def extract_mention_tokens(text: Optional[str]) -> List[str]:
    if not text:
        return []
    tokens: List[str] = []
    seen = set()
    for m in MENTION_RE.finditer(text):
        token = (m.group(1) or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return tokens


def _user_mention_aliases(u: User) -> set[str]:
    aliases = set()
    email = (u.email or "").strip().lower()
    if email:
        aliases.add(email)
        local = email.split("@")[0]
        if local:
            aliases.add(local)

    first = (u.first_name or "").strip().lower()
    last = (u.last_name or "").strip().lower()
    if first:
        aliases.add(first)
    if last:
        aliases.add(last)
    if first and last:
        aliases.add(f"{first}{last}")
        aliases.add(f"{first}.{last}")
        aliases.add(f"{first}_{last}")
    return aliases


async def resolve_mentions_to_users(
    db: AsyncSession,
    tenant_id: str,
    tokens: List[str],
) -> Dict[str, User]:
    if not tokens:
        return {}

    res = await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.is_active.is_(True))))
    users = res.scalars().all()

    token_map: Dict[str, User] = {}
    for raw in tokens:
        token = raw.strip().lower()
        if not token:
            continue
        for u in users:
            if token in _user_mention_aliases(u):
                token_map[raw] = u
                break

    return token_map


def _truncate(text: str, max_len: int) -> str:
    if text is None:
        return ""
    s = str(text)
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)] + "…"


async def create_mention_tasks_from_text(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str],
    actor_name: Optional[str],
    text: Optional[str],
    source: str,
    related_type: Optional[str],
    related_id: Optional[str],
    context_label: str,
) -> int:
    tokens = extract_mention_tokens(text)
    if not tokens:
        return 0

    token_to_user = await resolve_mentions_to_users(db, tenant_id, tokens)
    if not token_to_user:
        return 0

    now = now_utc()
    created = 0

    for token, mentioned_user in token_to_user.items():
        if actor_id and mentioned_user.id == actor_id:
            continue

        fingerprint_raw = f"{tenant_id}|{source}|{related_type or ''}|{related_id or ''}|{actor_id or ''}|{mentioned_user.id}|{token.lower()}"
        fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()[:24]

        existing_res = await db.execute(
            select(Task.id)
            .where(
                and_(
                    Task.tenant_id == tenant_id,
                    Task.owner_id == mentioned_user.id,
                    Task.status == "open",
                    Task.kind == "mention",
                    Task.meta["mention_fingerprint"].astext == fingerprint,
                )
            )
            .limit(1)
        )
        if existing_res.scalar_one_or_none():
            continue

        title = _truncate(f"Mention: {context_label}", 200)
        snippet = _truncate((text or "").strip(), 600)
        who = (actor_name or "Someone").strip() or "Someone"
        description = _truncate(
            f"{who} mentioned you (@{token}).\nContext: {context_label}\n\n{snippet}".strip(),
            1800,
        )

        task = Task(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=title,
            description=description or None,
            due_at=now + timedelta(hours=4),
            owner_id=mentioned_user.id,
            created_by=actor_id,
            status="open",
            kind="mention",
            related_type=(related_type or None),
            related_id=(related_id or None),
            completed_at=None,
            completed_by=None,
            meta={
                "mention": True,
                "mention_token": token,
                "mention_actor_id": actor_id,
                "mention_source": source,
                "mention_context_label": context_label,
                "mention_fingerprint": fingerprint,
                "created_at": now.isoformat(),
            },
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        created += 1

    if created:
        await db.flush()

    return created


async def _get_enabled_discord_webhook_url(db: AsyncSession, tenant_id: str) -> Optional[str]:
    res = await db.execute(
        select(WorkspaceIntegration).where(
            and_(
                WorkspaceIntegration.tenant_id == tenant_id,
                WorkspaceIntegration.provider_type == "discord",
                WorkspaceIntegration.enabled.is_(True),
            )
        )
    )
    integration = res.scalar_one_or_none()
    if not integration:
        return None

    enc = get_encryption_service()
    try:
        url = enc.decrypt(integration.encrypted_api_key)
    except Exception:
        return None

    url = (url or "").strip()
    if not url.startswith("https://discord.com/api/webhooks/") and not url.startswith("https://discordapp.com/api/webhooks/"):
        return None
    return url


async def _post_discord_webhook(webhook_url: str, content: str) -> bool:
    if not webhook_url or not content:
        return False
    if httpx is None:
        return False

    payload = {"content": _truncate(content, 1900)}
    timeout = httpx.Timeout(5.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(webhook_url, json=payload)
        return 200 <= resp.status_code < 300


async def maybe_send_discord_notification_for_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: str,
    title: str,
    actor_name: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    webhook_url = await _get_enabled_discord_webhook_url(db, tenant_id)
    if not webhook_url:
        return

    evt = (event_type or "").strip().lower()
    allowed = {"deal_won", "deal_lost", "lead_assigned", "form_submitted", "landing_page_conversion"}
    if evt not in allowed:
        return

    who = (actor_name or "").strip()
    prefix = f"[{evt}]"
    content = f"{prefix} {title}"
    if who:
        content = f"{content} (by {who})"

    try:
        ok = await _post_discord_webhook(webhook_url, content)
        if ok:
            res = await db.execute(
                select(WorkspaceIntegration).where(
                    and_(
                        WorkspaceIntegration.tenant_id == tenant_id,
                        WorkspaceIntegration.provider_type == "discord",
                    )
                )
            )
            integration = res.scalar_one_or_none()
            if integration:
                integration.last_used_at = now_utc()
                integration.updated_at = now_utc()
                await db.flush()
    except Exception:
        return

def normalize_sla_config(cfg: Optional[Dict[str, Any]]) -> Dict[str, int]:
    out = dict(DEFAULT_SLA_CONFIG)
    if not isinstance(cfg, dict):
        return out

    for key, default_val in DEFAULT_SLA_CONFIG.items():
        raw = cfg.get(key)
        if raw is None:
            continue
        try:
            value = int(raw)
        except Exception:
            continue
        if value <= 0:
            continue
        out[key] = value

    return out


async def get_workspace_sla_config(db: AsyncSession, tenant_id: str) -> Dict[str, int]:
    res = await db.execute(select(WorkspaceSetting).where(WorkspaceSetting.tenant_id == tenant_id).limit(1))
    ws = res.scalar_one_or_none()
    return normalize_sla_config((ws.sla_config or {}) if ws else None)


async def resolve_account(
    db: AsyncSession,
    tenant_id: str,
    account_name: str,
    actor_id: Optional[str],
    domain: Optional[str] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    country: Optional[str] = None,
    icp_tier: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    name = " ".join((account_name or "").strip().split())
    if not name:
        raise HTTPException(status_code=400, detail="account_name is required")

    name_lower = normalize_lower(name)
    normalized_domain = (domain or "").strip().lower()
    if normalized_domain.startswith("http://") or normalized_domain.startswith("https://"):
        normalized_domain = normalized_domain.split("://", 1)[1]
    if "/" in normalized_domain:
        normalized_domain = normalized_domain.split("/", 1)[0]
    if ":" in normalized_domain:
        normalized_domain = normalized_domain.split(":", 1)[0]
    normalized_domain = normalized_domain.strip().lstrip("www.")
    if not normalized_domain:
        normalized_domain = None

    account: Optional[Account] = None
    if normalized_domain:
        existing = await db.execute(
            select(Account).where(and_(Account.tenant_id == tenant_id, Account.domain_lower == normalized_domain))
        )
        account = existing.scalar_one_or_none()

    if not account:
        existing = await db.execute(
            select(Account).where(and_(Account.tenant_id == tenant_id, Account.name_lower == name_lower))
        )
        account = existing.scalar_one_or_none()

    if account:
        # Enrich existing records without overwriting deliberate values.
        if normalized_domain and not account.domain_lower:
            account.domain = normalized_domain
            account.domain_lower = normalized_domain
        if industry and not account.industry:
            account.industry = industry.strip()[:100]
        if company_size and not account.company_size:
            account.company_size = company_size.strip()[:100]
        if country and not account.country:
            account.country = country.strip()[:100]
        if icp_tier and not account.icp_tier:
            account.icp_tier = str(icp_tier).strip().upper()[:2]
        account.updated_at = now_utc()
        return {"account_id": account.id, "account_name": account.name or name}

    new_account = Account(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        name_lower=name_lower,
        domain=normalized_domain,
        domain_lower=normalized_domain,
        industry=(industry or "").strip()[:100] or None,
        company_size=(company_size or "").strip()[:100] or None,
        country=(country or "").strip()[:100] or None,
        icp_tier=(str(icp_tier).strip().upper()[:2] if icp_tier else None),
        is_active=True,
        created_by=actor_id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(new_account)
    await db.flush()
    return {"account_id": new_account.id, "account_name": new_account.name}


async def resolve_partner_and_product(
    db: AsyncSession,
    tenant_id: str,
    sales_motion_type: str,
    partner_id: Optional[str],
    product_id: Optional[str],
    partner_name: Optional[str],
    product_name: Optional[str],
    actor_id: Optional[str],
) -> Dict[str, Optional[str]]:
    sales_motion_type = (sales_motion_type or "partnership_sales").strip()
    if sales_motion_type not in {"partnership_sales", "partner_sales"}:
        raise HTTPException(status_code=400, detail="Invalid sales_motion_type")

    if sales_motion_type == "partnership_sales":
        return {"partner_id": None, "partner_name": None, "product_id": None, "product_name": None}

    # Partner
    partner: Optional[Partner] = None
    if partner_id:
        partner_res = await db.execute(
            select(Partner).where(and_(Partner.id == partner_id, Partner.tenant_id == tenant_id))
        )
        partner = partner_res.scalar_one_or_none()
        if not partner:
            raise HTTPException(status_code=400, detail="Partner not found")
        partner_name = partner.name
    else:
        name = (partner_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="partner_name is required for partner_sales")
        name_lower = normalize_lower(name)
        partner_res = await db.execute(
            select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.name_lower == name_lower))
        )
        partner = partner_res.scalar_one_or_none()
        if not partner:
            partner = Partner(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                name_lower=name_lower,
                is_active=True,
                created_by=actor_id,
                created_at=now_utc(),
                updated_at=now_utc(),
            )
            db.add(partner)
            await db.flush()
        partner_id = partner.id
        partner_name = partner.name

    # Product
    product: Optional[Product] = None
    if product_id:
        product_res = await db.execute(
            select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
        )
        product = product_res.scalar_one_or_none()
        if not product or product.partner_id != partner_id:
            raise HTTPException(status_code=400, detail="Product not found for partner")
        product_name = product.name
    else:
        name = (product_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="product_name is required for partner_sales")
        name_lower = normalize_lower(name)
        product_res = await db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.partner_id == partner_id,
                    Product.name_lower == name_lower,
                )
            )
        )
        product = product_res.scalar_one_or_none()
        if not product:
            product = Product(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                partner_id=partner_id,
                name=name,
                name_lower=name_lower,
                is_active=True,
                created_by=actor_id,
                created_at=now_utc(),
                updated_at=now_utc(),
            )
            db.add(product)
            await db.flush()
        product_id = product.id
        product_name = product.name

    return {
        "partner_id": partner_id,
        "partner_name": partner_name,
        "product_id": product_id,
        "product_name": product_name,
    }


async def create_timeline_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: str,
    title: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    deal_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    description: Optional[str] = None,
    visibility: str = "internal_only",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    created_at = now_utc()
    event = TimelineEvent(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_id=actor_id,
        actor_name=actor_name,
        deal_id=deal_id,
        contact_id=contact_id,
        visibility=visibility,
        meta=metadata or {},
        created_at=created_at,
    )
    db.add(event)
    await db.flush()

    # Cadence tracking: keep a fast "last touched" timestamp on deals.
    evt_type = (event_type or "").strip()
    if deal_id and evt_type in TOUCHPOINT_EVENT_TYPES:
        deal = (
            await db.execute(select(Deal).where(and_(Deal.tenant_id == tenant_id, Deal.id == deal_id)).limit(1))
        ).scalar_one_or_none()
        if deal:
            if not deal.last_touchpoint_at or deal.last_touchpoint_at < created_at:
                deal.last_touchpoint_at = created_at
                deal.updated_at = now_utc()
                await db.flush()

    # @mentions: create "mention" tasks for any referenced teammates in title/description.
    try:
        mention_text = " ".join([x for x in [(title or "").strip(), (description or "").strip()] if x])
        if mention_text:
            rt = "deal" if deal_id else ("contact" if contact_id else None)
            rid = deal_id or contact_id
            await create_mention_tasks_from_text(
                db=db,
                tenant_id=tenant_id,
                actor_id=actor_id,
                actor_name=actor_name,
                text=mention_text,
                source=f"timeline:{event.id}",
                related_type=rt,
                related_id=rid,
                context_label=title,
            )
    except Exception:
        pass

    # Discord automation (webhook): key events only (wins + lead assignment).
    try:
        await maybe_send_discord_notification_for_event(
            db=db,
            tenant_id=tenant_id,
            event_type=event_type,
            title=title,
            actor_name=actor_name,
            metadata=metadata or {},
        )
    except Exception:
        pass

    # Workflow automation trigger bus (real-time).
    try:
        trigger_map = {
            "form_submitted": "form_submitted",
            "stage_changed": "deal_stage_changed",
            "deal_created": "deal_created",
            "contact_created": "contact_created",
            "landing_page_view": "landing_page_view",
            "landing_page_conversion": "landing_page_conversion",
            "message_received": "message_received",
        }
        trigger_type = trigger_map.get((event_type or "").strip().lower())
        if trigger_type:
            from app.api_pg.workflow_engine import trigger_workflows_for_event

            trigger_payload = {
                "event_type": event_type,
                "title": title,
                "description": description,
                **(metadata or {}),
            }
            await trigger_workflows_for_event(
                db=db,
                tenant_id=tenant_id,
                trigger_type=trigger_type,
                trigger_data=trigger_payload,
                contact_id=contact_id,
                deal_id=deal_id,
            )
    except Exception:
        pass

    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "deal_id": event.deal_id,
        "contact_id": event.contact_id,
        "visibility": event.visibility,
        "metadata": event.meta or {},
        "created_at": event.created_at.isoformat(),
    }


async def complete_open_next_step_tasks_for_deal(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    completed_by: Optional[str],
) -> int:
    now = now_utc()
    result = await db.execute(
        update(Task)
        .where(
            and_(
                Task.tenant_id == tenant_id,
                Task.related_type == "deal",
                Task.related_id == deal_id,
                Task.kind == "next_step",
                Task.status == "open",
            )
        )
        .values(status="completed", completed_at=now, completed_by=completed_by, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)


async def upsert_open_next_step_task_for_deal(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    due_at: datetime,
    owner_id: Optional[str],
    created_by: Optional[str],
    note: Optional[str] = None,
) -> None:
    existing_res = await db.execute(
        select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.related_type == "deal",
                Task.related_id == deal_id,
                Task.kind == "next_step",
                Task.status == "open",
            )
        )
    )
    task = existing_res.scalar_one_or_none()
    now = now_utc()
    if task:
        task.due_at = due_at
        task.owner_id = owner_id
        task.description = note
        task.updated_at = now
        return

    new_task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title="Next Step",
        description=note,
        status="open",
        kind="next_step",
        due_at=due_at,
        owner_id=owner_id,
        related_type="deal",
        related_id=deal_id,
        created_by=created_by,
        meta={},
        created_at=now,
        updated_at=now,
    )
    db.add(new_task)
    await db.flush()


async def get_default_pipeline_and_stage(
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: Optional[str],
    stage_id: Optional[str],
    sales_motion_type: Optional[str] = None,
    partner_id: Optional[str] = None,
) -> Dict[str, Any]:
    pipeline: Optional[Pipeline] = None
    if pipeline_id:
        pipeline_res = await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
        pipeline = pipeline_res.scalar_one_or_none()
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    else:
        if (sales_motion_type or "").strip() == "partner_sales" and partner_id:
            partner = (
                await db.execute(select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.id == partner_id)))
            ).scalar_one_or_none()
            if partner and partner.default_pipeline_id:
                pipeline = (
                    await db.execute(
                        select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.id == partner.default_pipeline_id))
                    )
                ).scalar_one_or_none()

        pipeline_res = await db.execute(
            select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default == True)).limit(1)
        )
        pipeline = pipeline or pipeline_res.scalar_one_or_none()
        if not pipeline:
            pipeline_res = await db.execute(select(Pipeline).where(Pipeline.tenant_id == tenant_id).limit(1))
            pipeline = pipeline_res.scalar_one_or_none()
        if not pipeline:
            raise HTTPException(status_code=400, detail="No pipelines configured for tenant")

    stage: Optional[PipelineStage] = None
    if stage_id:
        stage_res = await db.execute(
            select(PipelineStage).where(and_(PipelineStage.id == stage_id, PipelineStage.pipeline_id == pipeline.id))
        )
        stage = stage_res.scalar_one_or_none()
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
    else:
        stage_res = await db.execute(
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline.id).order_by(PipelineStage.display_order.asc()).limit(1)
        )
        stage = stage_res.scalar_one_or_none()
        if not stage:
            raise HTTPException(status_code=400, detail="No stages configured for pipeline")

    return {"pipeline": pipeline, "stage": stage}


async def get_active_calculation_definition(db: AsyncSession, tenant_id: str) -> Optional[CalculationDefinition]:
    res = await db.execute(
        select(CalculationDefinition)
        .where(and_(CalculationDefinition.tenant_id == tenant_id, CalculationDefinition.is_active == True))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_calculation_result(
    db: AsyncSession, deal_id: str, definition_id: str
) -> Optional[CalculationResult]:
    res = await db.execute(
        select(CalculationResult).where(and_(CalculationResult.deal_id == deal_id, CalculationResult.definition_id == definition_id))
    )
    return res.scalar_one_or_none()


async def get_or_create_deal_handoff(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    actor_id: Optional[str],
) -> DealHandoff:
    res = await db.execute(
        select(DealHandoff).where(and_(DealHandoff.tenant_id == tenant_id, DealHandoff.deal_id == deal_id))
    )
    handoff = res.scalar_one_or_none()
    if handoff:
        return handoff

    now = now_utc()
    handoff = DealHandoff(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        deal_id=deal_id,
        delivery_owner_id=None,
        kickoff_at=None,
        checklist={},
        notes=None,
        status="pending",
        completed_at=None,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(handoff)
    await db.flush()
    return handoff


def handoff_complete(delivery_owner_id: Optional[str], kickoff_at: Any, checklist: Dict[str, Any]) -> bool:
    if not delivery_owner_id:
        return False
    if not kickoff_at:
        return False

    required_keys = [
        "spiced_summary",
        "gap_analysis",
        "proposal",
        "contract",
        "risk_notes",
        "kickoff_readiness_checklist",
    ]
    checklist = checklist or {}
    return all(bool(checklist.get(k)) for k in required_keys)


async def sync_deal_handoff_status(
    db: AsyncSession,
    tenant_id: str,
    deal: Deal,
    handoff: DealHandoff,
    actor: Dict[str, Any],
) -> None:
    complete = handoff_complete(handoff.delivery_owner_id, handoff.kickoff_at, handoff.checklist or {})
    now = now_utc()

    if complete and handoff.status != "completed":
        handoff.status = "completed"
        handoff.completed_at = now
        handoff.updated_at = now
        deal.handoff_status = "completed"
        deal.handoff_completed_at = now
        deal.updated_at = now
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="handoff_completed",
            title="Delivery handoff completed",
            actor_id=actor.get("id"),
            actor_name=actor.get("full_name"),
            deal_id=deal.id,
            metadata={"handoff_id": handoff.id},
        )
        return

    if not complete and handoff.status == "completed":
        handoff.status = "pending"
        handoff.completed_at = None
        handoff.updated_at = now
        deal.handoff_status = "pending"
        deal.handoff_completed_at = None
        deal.updated_at = now


async def _active_users_by_roles(db: AsyncSession, tenant_id: str, roles: set[str]) -> List[User]:
    if not roles:
        return []
    rows = await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.is_active.is_(True))))
    users = rows.scalars().all()
    return [u for u in users if (u.role or "").strip().lower() in roles]


async def _first_manager_id(db: AsyncSession, tenant_id: str) -> Optional[str]:
    managers = await _active_users_by_roles(db, tenant_id, MANAGER_ROLES)
    return managers[0].id if managers else None


async def _finance_users(db: AsyncSession, tenant_id: str) -> List[User]:
    return await _active_users_by_roles(db, tenant_id, FINANCE_ROLES)


async def upsert_open_task_by_rule(
    db: AsyncSession,
    tenant_id: str,
    rule_key: str,
    title: str,
    due_at: datetime,
    owner_id: Optional[str],
    created_by: Optional[str],
    kind: str,
    related_type: Optional[str],
    related_id: Optional[str],
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    if not rule_key:
        return False

    existing_res = await db.execute(
        select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.status == "open",
                Task.meta["rule_key"].astext == rule_key,
            )
        )
    )
    existing = existing_res.scalar_one_or_none()
    now = now_utc()
    payload_meta = {"rule_key": rule_key, **(metadata or {})}

    if existing:
        existing.title = title
        existing.description = description
        existing.due_at = due_at
        existing.owner_id = owner_id
        existing.kind = kind
        existing.related_type = related_type
        existing.related_id = related_id
        existing.meta = payload_meta
        existing.updated_at = now
        return False

    task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=title,
        description=description,
        due_at=due_at,
        owner_id=owner_id,
        created_by=created_by,
        status="open",
        kind=kind,
        related_type=related_type,
        related_id=related_id,
        completed_at=None,
        completed_by=None,
        meta=payload_meta,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()
    return True


def _is_affiliate_source(source: Optional[str]) -> bool:
    s = (source or "").strip().lower()
    return "affiliate" in s


def _default_handoff_checklist() -> Dict[str, bool]:
    return {
        "spiced_summary": False,
        "gap_analysis": False,
        "proposal": False,
        "contract": False,
        "risk_notes": False,
        "kickoff_readiness_checklist": False,
    }


async def run_lead_sla_automations(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = "System",
) -> None:
    now = now_utc()
    manager_id = await _first_manager_id(db, tenant_id)
    leads = (
        await db.execute(
            select(Lead).where(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.status.in_(list(LEAD_ACTIVE_STATUSES)),
                )
            )
        )
    ).scalars().all()

    for lead in leads:
        if (lead.status or "").strip().lower() in {"converted", "disqualified"}:
            continue

        created_at = lead.created_at or now
        owner_id = lead.owner_id or manager_id or actor_id
        no_touch = (lead.first_touchpoint_at is None) and int(lead.touchpoints_count or 0) == 0
        elapsed_minutes = max(0.0, (now - created_at).total_seconds() / 60.0)

        if no_touch and (lead.status or "").strip().lower() in {"new", "assigned", "new_assigned"}:
            await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"lead:first-response:{lead.id}",
                title="First response required",
                description="New lead requires first outreach within SLA window.",
                due_at=created_at + timedelta(minutes=15),
                owner_id=owner_id,
                created_by=actor_id,
                kind=LEAD_SLA_TASK_KIND,
                related_type="lead",
                related_id=lead.id,
                metadata={"severity": "warning"},
            )

        if no_touch and _is_affiliate_source(lead.source) and elapsed_minutes >= 15:
            created = await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"lead:affiliate-15m:{lead.id}",
                title="Affiliate lead SLA breach (15m)",
                description="Affiliate lead has no activity for at least 15 minutes.",
                due_at=now,
                owner_id=owner_id,
                created_by=actor_id,
                kind=LEAD_SLA_TASK_KIND,
                related_type="lead",
                related_id=lead.id,
                metadata={"severity": "high", "source": lead.source},
            )
            if created:
                await create_timeline_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type="lead_sla_breach_15m",
                    title="Affiliate lead SLA breach",
                    actor_id=actor_id,
                    actor_name=actor_name,
                    metadata={"lead_id": lead.id, "elapsed_minutes": round(elapsed_minutes, 1)},
                )

        if no_touch and elapsed_minutes >= 24 * 60:
            escalation_owner = manager_id or owner_id
            created = await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"lead:escalation-24h:{lead.id}",
                title="Lead escalation: no activity in 24h",
                description="Lead has no activity after 24 hours and requires manager escalation.",
                due_at=now,
                owner_id=escalation_owner,
                created_by=actor_id,
                kind=LEAD_SLA_TASK_KIND,
                related_type="lead",
                related_id=lead.id,
                metadata={"severity": "critical"},
            )
            if created:
                await create_timeline_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type="lead_sla_escalation_24h",
                    title="Lead escalated after 24h inactivity",
                    actor_id=actor_id,
                    actor_name=actor_name,
                    metadata={"lead_id": lead.id},
                )


async def run_deal_stale_automations(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = "System",
) -> None:
    now = now_utc()
    manager_id = await _first_manager_id(db, tenant_id)
    deals = (
        await db.execute(
            select(Deal).where(
                and_(
                    Deal.tenant_id == tenant_id,
                    Deal.status == "open",
                )
            )
        )
    ).scalars().all()

    stage_ids = [d.stage_id for d in deals if d.stage_id]
    stages: Dict[str, PipelineStage] = {}
    if stage_ids:
        stage_rows = (await db.execute(select(PipelineStage).where(PipelineStage.id.in_(stage_ids)))).scalars().all()
        stages = {s.id: s for s in stage_rows}

    updated_deals = False
    for deal in deals:
        baseline = deal.last_touchpoint_at or deal.updated_at or deal.created_at
        if not baseline:
            continue
        stale_days = int((now - baseline).total_seconds() // 86400)
        stage = stages.get(deal.stage_id) if deal.stage_id else None
        stage_order = int(stage.display_order or 0) if stage else 0
        early_stage = stage_order <= 4
        owner_id = deal.owner_id or manager_id or actor_id

        if early_stage and stale_days >= 3:
            await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"deal:stale-3d:{deal.id}",
                title="Deal reminder: stale for 3 days",
                description="No activity detected in an early-stage deal for 3 days.",
                due_at=now,
                owner_id=owner_id,
                created_by=actor_id,
                kind=DEAL_RISK_TASK_KIND,
                related_type="deal",
                related_id=deal.id,
                metadata={"severity": "warning", "stale_days": stale_days},
            )

        if stale_days >= 7:
            await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"deal:stale-7d:{deal.id}",
                title="Deal escalation: stale for 7 days",
                description="Deal requires manager attention after 7 days without activity.",
                due_at=now,
                owner_id=manager_id or owner_id,
                created_by=actor_id,
                kind=DEAL_RISK_TASK_KIND,
                related_type="deal",
                related_id=deal.id,
                metadata={"severity": "high", "stale_days": stale_days},
            )

        if stale_days >= 14:
            await upsert_open_task_by_rule(
                db=db,
                tenant_id=tenant_id,
                rule_key=f"deal:stale-14d:{deal.id}",
                title="Deal at risk: stale for 14 days",
                description="Deal auto-flagged as At Risk due to inactivity.",
                due_at=now,
                owner_id=manager_id or owner_id,
                created_by=actor_id,
                kind=DEAL_RISK_TASK_KIND,
                related_type="deal",
                related_id=deal.id,
                metadata={"severity": "critical", "stale_days": stale_days},
            )
            if not bool(deal.at_risk):
                deal.at_risk = True
                deal.updated_at = now
                updated_deals = True
                await create_timeline_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type="deal_at_risk",
                    title="Deal auto-flagged At Risk",
                    actor_id=actor_id,
                    actor_name=actor_name,
                    deal_id=deal.id,
                    metadata={"stale_days": stale_days},
                )
        elif bool(deal.at_risk):
            deal.at_risk = False
            deal.updated_at = now
            updated_deals = True

    if updated_deals:
        await db.flush()


async def run_crm_automations(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = "System",
) -> None:
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=actor_id, actor_name=actor_name)
    await run_deal_stale_automations(db, tenant_id=tenant_id, actor_id=actor_id, actor_name=actor_name)


async def apply_closed_won_automations(
    db: AsyncSession,
    tenant_id: str,
    deal: Deal,
    actor: Dict[str, Any],
) -> None:
    now = now_utc()
    actor_id = actor.get("id")
    actor_name = actor.get("full_name")

    handoff = await get_or_create_deal_handoff(db, tenant_id, deal.id, actor_id)
    if not handoff.checklist:
        handoff.checklist = _default_handoff_checklist()
    if not handoff.delivery_owner_id:
        handoff.delivery_owner_id = await _first_manager_id(db, tenant_id) or deal.owner_id
    handoff.updated_at = now

    deal.deal_locked = True
    deal.handoff_status = handoff.status or "pending"
    deal.updated_at = now

    kickoff_owner = handoff.delivery_owner_id or deal.owner_id or actor_id
    await upsert_open_task_by_rule(
        db=db,
        tenant_id=tenant_id,
        rule_key=f"deal:kickoff:{deal.id}",
        title="Create delivery kickoff plan",
        description="Closed Won trigger: set kickoff date and complete handoff checklist.",
        due_at=now + timedelta(days=1),
        owner_id=kickoff_owner,
        created_by=actor_id,
        kind=KICKOFF_TASK_KIND,
        related_type="deal",
        related_id=deal.id,
        metadata={"closed_won": True},
    )

    finance_users = await _finance_users(db, tenant_id)
    for finance_user in finance_users:
        await upsert_open_task_by_rule(
            db=db,
            tenant_id=tenant_id,
            rule_key=f"deal:finance-notify:{deal.id}:{finance_user.id}",
            title="Finance review: closed won deal",
            description=f"Deal '{deal.name}' requires finance review and commission processing.",
            due_at=now,
            owner_id=finance_user.id,
            created_by=actor_id,
            kind="finance_notice",
            related_type="deal",
            related_id=deal.id,
            metadata={"closed_won": True},
        )

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="deal_closed_won_automation",
        title="Closed Won automations executed",
        actor_id=actor_id,
        actor_name=actor_name,
        deal_id=deal.id,
        metadata={
            "deal_locked": True,
            "delivery_owner_id": handoff.delivery_owner_id,
            "finance_notifications": len(finance_users),
        },
    )
