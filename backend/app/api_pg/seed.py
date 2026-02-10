from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_password_hash
from app.api_pg.utils import normalize_lower, now_utc
from app.pg_models.models import (
    AIUsageConfig,
    Affiliate,
    AffiliateLink,
    AffiliateProgram,
    AffiliateSetting,
    CRMBlueprint,
    Campaign,
    CalculationDefinition,
    Conversation,
    CustomObjectDefinition,
    CustomObjectField,
    CustomObjectRecord,
    LandingPage,
    LandingPageVersion,
    MarketingList,
    MarketingMaterial,
    Message,
    Pipeline,
    PipelineStage,
    Tenant,
    User,
    WorkspaceSetting,
    Workflow,
    WorkflowBlueprint,
)


async def seed_demo_data(db: AsyncSession) -> None:
    """Seed demo tenant + minimal data for Phase 1 + Phase 2 modules.

    Idempotent for the `demo` tenant: creates missing demo rows without overwriting user data.
    """
    now = now_utc()

    existing = await db.execute(select(Tenant).where(Tenant.slug == "demo"))
    tenant = existing.scalar_one_or_none()

    if not tenant:
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Demo Company",
            slug="demo",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(tenant)
        await db.flush()

    tenant_id = tenant.id

    desired_users = [
        ("admin@demo.com", "admin123", "Admin", "User", "admin"),
        ("manager@demo.com", "manager123", "Manager", "User", "manager"),
        ("sales@demo.com", "sales123", "Sales", "Rep", "sales"),
    ]

    user_ids: dict[str, str] = {}
    for email, password, first_name, last_name, role in desired_users:
        user_res = await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.email == email)))
        user = user_res.scalar_one_or_none()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                email=email,
                hashed_password=get_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            await db.flush()
        user_ids[email] = user.id

    admin_user_id = user_ids["admin@demo.com"]

    pipeline_res = await db.execute(
        select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True))).limit(1)
    )
    pipeline = pipeline_res.scalar_one_or_none()
    if not pipeline:
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Elev8 Sales Pipeline",
            description="Playbook-aligned sales pipeline (Phase 1)",
            is_default=True,
            display_order=0,
            created_at=now,
            updated_at=now,
        )
        db.add(pipeline)
        await db.flush()

    pipeline_id = pipeline.id

    stage_res = await db.execute(select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).limit(1))
    stage_any = stage_res.scalar_one_or_none()

    calc_stage_id: str | None = None

    if not stage_any:
        stages_data = [
            {
                "name": "Calculations / Analysis In Progress",
                "color": "#6366F1",
                "probability": 15,
                "required_fields": ["next_step_at", "contact_id"],
            },
            {
                "name": "Discovery / Demo Scheduled",
                "color": "#8B5CF6",
                "probability": 25,
                "required_fields": ["next_step_at", "contact_id"],
                "requires_calculation_complete": True,
            },
            {
                "name": "Discovery / Demo Completed",
                "color": "#A855F7",
                "probability": 35,
                "required_fields": ["next_step_at", "contact_id"],
            },
            {"name": "Decision Pending", "color": "#C084FC", "probability": 45, "required_fields": ["next_step_at", "contact_id"]},
            {"name": "Trial / Pilot", "color": "#D946EF", "probability": 55, "required_fields": ["next_step_at", "contact_id"]},
            {"name": "Verbal Commitment", "color": "#EC4899", "probability": 65, "required_fields": ["next_step_at", "contact_id"]},
            {"name": "Closed Won", "color": "#10B981", "probability": 100, "required_fields": []},
            {"name": "Closed Lost", "color": "#EF4444", "probability": 0, "required_fields": []},
            {"name": "Handoff to Delivery", "color": "#F97316", "probability": 100, "required_fields": []},
        ]

        for order, cfg in enumerate(stages_data):
            stage_id = str(uuid.uuid4())
            if order == 0:
                calc_stage_id = stage_id
            db.add(
                PipelineStage(
                    id=stage_id,
                    pipeline_id=pipeline_id,
                    name=cfg["name"],
                    color=cfg.get("color") or "#6366F1",
                    display_order=order,
                    probability=float(cfg.get("probability") or 0),
                    required_fields=list(cfg.get("required_fields") or []),
                    requires_calculation_complete=bool(cfg.get("requires_calculation_complete") or False),
                    created_at=now,
                    updated_at=now,
                )
            )
        await db.flush()
    else:
        stage0_res = await db.execute(
            select(PipelineStage.id)
            .where(and_(PipelineStage.pipeline_id == pipeline_id, PipelineStage.display_order == 0))
            .limit(1)
        )
        calc_stage_id = stage0_res.scalar_one_or_none()

    calc_res = await db.execute(
        select(CalculationDefinition).where(
            and_(CalculationDefinition.tenant_id == tenant_id, CalculationDefinition.name == "Frylow ROI Calculator")
        )
    )
    if not calc_res.scalar_one_or_none():
        # Minimal ROI calculator definition (Phase 1 gating)
        db.add(
            CalculationDefinition(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name="Frylow ROI Calculator",
                description="Calculate oil savings and recommended device configuration",
                input_schema=[
                    {"name": "number_of_fryers", "type": "integer", "label": "Number of Fryers", "required": True, "min": 1, "max": 50},
                    {
                        "name": "fryer_capacities",
                        "type": "multi_select",
                        "label": "Fryer Capacities",
                        "required": True,
                        "options": [{"value": "16L", "label": "16 Liters"}, {"value": "30L", "label": "30 Liters"}, {"value": "45L", "label": "45 Liters"}],
                    },
                    {
                        "name": "oil_units",
                        "type": "select",
                        "label": "Oil Purchase Units",
                        "required": True,
                        "options": [{"value": "boxes", "label": "Boxes"}, {"value": "gallons", "label": "Gallons"}],
                    },
                    {"name": "quantity_per_month", "type": "integer", "label": "Quantity Per Month", "required": True, "min": 1},
                    {"name": "cost_per_unit", "type": "currency", "label": "Cost Per Unit ($)", "required": True, "min": 0},
                ],
                output_schema=[
                    {"name": "monthly_oil_spend", "type": "currency", "label": "Monthly Oil Spend"},
                    {"name": "yearly_oil_spend", "type": "currency", "label": "Yearly Oil Spend"},
                    {"name": "estimated_savings_low", "type": "currency", "label": "Estimated Savings (Low)"},
                    {"name": "estimated_savings_high", "type": "currency", "label": "Estimated Savings (High)"},
                    {"name": "recommended_device_quantity", "type": "integer", "label": "Recommended Devices"},
                    {"name": "recommended_device_size", "type": "text", "label": "Recommended Size"},
                ],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- Workspace Settings (Phase 2) --------------------
    ws_res = await db.execute(select(WorkspaceSetting).where(WorkspaceSetting.tenant_id == tenant_id))
    if not ws_res.scalar_one_or_none():
        db.add(
            WorkspaceSetting(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=tenant.name,
                description="Demo workspace settings",
                logo_url=None,
                primary_color="#F97316",
                timezone="UTC",
                currency="USD",
                updated_by=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )

    ai_cfg_res = await db.execute(select(AIUsageConfig).where(AIUsageConfig.tenant_id == tenant_id))
    if not ai_cfg_res.scalar_one_or_none():
        db.add(
            AIUsageConfig(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                default_provider="openai",
                default_model="gpt-4o-mini",
                provider_overrides={},
                usage_limits={"daily_requests": 250, "monthly_requests": 5000},
                features_enabled={"landing_pages": True, "chat": True},
                updated_by=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- CRM Blueprints (Phase 2) --------------------
    bp_res = await db.execute(select(CRMBlueprint).where(CRMBlueprint.tenant_id == tenant_id).limit(1))
    if not bp_res.scalar_one_or_none():
        from app.blueprints.frylow_blueprint import get_all_blueprints

        for bp in get_all_blueprints():
            cfg = bp.get("config") or {}
            db.add(
                CRMBlueprint(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    name=bp.get("name") or cfg.get("name") or bp["slug"],
                    slug=bp["slug"],
                    description=cfg.get("description"),
                    version=int(cfg.get("version") or 1),
                    icon=cfg.get("icon", "building"),
                    color=cfg.get("color", "#6366F1"),
                    is_default=bool(bp.get("is_default")),
                    is_system=True,
                    is_active=True,
                    config=cfg,
                    created_at=now,
                    updated_at=now,
                )
            )

    # -------------------- Workflow Blueprints (Phase 2) --------------------
    wfb_res = await db.execute(select(WorkflowBlueprint).where(WorkflowBlueprint.tenant_id == tenant_id).limit(1))
    if not wfb_res.scalar_one_or_none():
        stages = [
            {"id": str(uuid.uuid4()), "name": "New Lead", "color": "#6366F1", "is_milestone": True},
            {"id": str(uuid.uuid4()), "name": "Contacted", "color": "#8B5CF6", "is_milestone": False},
            {"id": str(uuid.uuid4()), "name": "Qualified", "color": "#10B981", "is_milestone": True},
        ]
        db.add(
            WorkflowBlueprint(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name="Sales Follow-up Blueprint",
                description="Example workflow blueprint for the demo workspace",
                stages=stages,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- Workflows (Phase 2) --------------------
    wf_res = await db.execute(select(Workflow).where(Workflow.tenant_id == tenant_id).limit(1))
    if not wf_res.scalar_one_or_none():
        db.add(
            Workflow(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name="Demo Follow-up Workflow",
                description="Sample workflow used for UI validation",
                status="active",
                trigger_type="form_submitted",
                trigger_config={"form_slug": "demo-form"},
                actions=[{"type": "create_task", "title": "Follow up within 24h", "due_hours": 24}],
                total_runs=0,
                successful_runs=0,
                failed_runs=0,
                created_by=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- Landing Pages (Phase 2) --------------------
    lp_res = await db.execute(select(LandingPage).where(LandingPage.tenant_id == tenant_id).limit(1))
    if not lp_res.scalar_one_or_none():
        landing_page_id = str(uuid.uuid4())
        page_schema = {
            "title": "Demo Landing Page",
            "sections": [
                {"type": "hero", "headline": "Save 30% on oil costs", "subheadline": "See your ROI instantly"},
                {"type": "cta", "buttonText": "Book a Demo", "link": "https://example.com/book"},
            ],
        }
        db.add(
            LandingPage(
                id=landing_page_id,
                tenant_id=tenant_id,
                name="Demo Offer Page",
                slug="demo-offer",
                page_type="generic",
                status="published",
                version=1,
                page_schema=page_schema,
                affiliate_program_id=None,
                product_id=None,
                ai_model_used=None,
                custom_slug=None,
                seo_title="Demo Offer",
                seo_description="Demo landing page for Phase 2 testing",
                view_count=0,
                conversion_count=0,
                created_by=admin_user_id,
                created_at=now,
                updated_at=now,
                published_at=now,
                deleted_at=None,
            )
        )
        db.add(
            LandingPageVersion(
                id=str(uuid.uuid4()),
                landing_page_id=landing_page_id,
                version_number=1,
                page_schema=page_schema,
                created_by=admin_user_id,
                created_at=now,
            )
        )

    # -------------------- Inbox (Phase 2) --------------------
    convo_res = await db.execute(select(Conversation).where(Conversation.tenant_id == tenant_id).limit(1))
    if not convo_res.scalar_one_or_none():
        conversation_id = str(uuid.uuid4())
        db.add(
            Conversation(
                id=conversation_id,
                tenant_id=tenant_id,
                contact_id=None,
                channel="email",
                subject="Welcome to Elevate CRM",
                is_open=True,
                is_read=True,
                message_count=1,
                unread_count=0,
                last_message_preview="This is a seeded message for the Inbox UI.",
                last_message_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            Message(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                channel="email",
                direction="inbound",
                status="received",
                from_address="customer@example.com",
                to_address="sales@demo.com",
                subject="Welcome to Elevate CRM",
                body="This is a seeded message for the Inbox UI.",
                body_html=None,
                sent_by_user_id=None,
                sent_by_name="Demo Customer",
                sent_at=now,
                created_at=now,
            )
        )

    # -------------------- Lists + Campaigns (Phase 2) --------------------
    list_res = await db.execute(select(MarketingList).where(MarketingList.tenant_id == tenant_id).limit(1))
    marketing_list = list_res.scalar_one_or_none()
    if not marketing_list:
        marketing_list = MarketingList(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Demo List",
            description="Seeded list for Campaigns UI",
            type="static",
            filters=None,
            created_by=admin_user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(marketing_list)
        await db.flush()

    camp_res = await db.execute(select(Campaign).where(Campaign.tenant_id == tenant_id).limit(1))
    if not camp_res.scalar_one_or_none():
        db.add(
            Campaign(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name="Demo Email Campaign",
                subject="Demo Campaign Subject",
                content="Hello from Elevate CRM! This is seeded content.",
                campaign_type="email",
                status="draft",
                list_id=marketing_list.id,
                scheduled_at=None,
                sent_at=None,
                sent_count=0,
                delivered_count=0,
                open_count=0,
                click_count=0,
                bounce_count=0,
                unsubscribe_count=0,
                created_by=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- Affiliate Program + Portal Demo (Phase 2) --------------------
    aff_settings_res = await db.execute(select(AffiliateSetting).where(AffiliateSetting.tenant_id == tenant_id))
    if not aff_settings_res.scalar_one_or_none():
        db.add(
            AffiliateSetting(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                enabled=True,
                default_currency="USD",
                default_attribution_window_days=30,
                approval_mode="manual",
                min_payout_threshold=50.0,
                meta={},
                updated_by=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )

    program_res = await db.execute(select(AffiliateProgram).where(AffiliateProgram.tenant_id == tenant_id).limit(1))
    program = program_res.scalar_one_or_none()
    if not program:
        program = AffiliateProgram(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Demo Affiliate Program",
            name_lower=normalize_lower("Demo Affiliate Program"),
            description="Seeded affiliate program for Phase 2 testing",
            product_type="service",
            journey_type="demo_first",
            attribution_type="deal",
            attribution_model="first_touch",
            attribution_window_days=30,
            commission_type="percentage",
            commission_value=10.0,
            min_payout_threshold=50.0,
            cookie_duration_days=30,
            pipeline_scope=pipeline_id,
            qualifying_stage_id=calc_stage_id,
            auto_approve=False,
            is_active=True,
            created_by=admin_user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(program)
        await db.flush()

    affiliate_email = "affiliate@demo.com"
    affiliate_res = await db.execute(
        select(Affiliate).where(and_(Affiliate.tenant_id == tenant_id, Affiliate.email == affiliate_email))
    )
    affiliate = affiliate_res.scalar_one_or_none()
    if not affiliate:
        affiliate = Affiliate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Demo Affiliate",
            email=affiliate_email,
            password_hash=get_password_hash("affiliate123"),
            phone=None,
            company="Demo Co",
            website=None,
            status="active",
            payout_method="manual",
            payout_details={},
            notes=None,
            total_earnings=0.0,
            total_paid=0.0,
            created_at=now,
            updated_at=now,
        )
        db.add(affiliate)
        await db.flush()

    link_res = await db.execute(
        select(AffiliateLink)
        .where(and_(AffiliateLink.tenant_id == tenant_id, AffiliateLink.affiliate_id == affiliate.id))
        .limit(1)
    )
    if not link_res.scalar_one_or_none():
        db.add(
            AffiliateLink(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                affiliate_id=affiliate.id,
                program_id=program.id,
                referral_code="DEMOAFF1",
                landing_page_url="http://localhost:3000/pages/demo-offer",
                utm_source="affiliate",
                utm_medium="referral",
                utm_campaign="demo",
                click_count=0,
                conversion_count=0,
                is_active=True,
                created_at=now,
            )
        )

    mat_res = await db.execute(select(MarketingMaterial).where(MarketingMaterial.tenant_id == tenant_id).limit(1))
    if not mat_res.scalar_one_or_none():
        db.add(
            MarketingMaterial(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name="Demo Banner",
                description="Seeded marketing material for the affiliate portal",
                category="banners",
                material_type="url",
                file_path=None,
                file_name=None,
                file_size=0,
                content_type=None,
                storage_provider=None,
                url="https://placehold.co/1200x628/png",
                program_id=program.id,
                tags=["demo", "banner"],
                download_count=0,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    # -------------------- Custom Objects (Phase 2) --------------------
    obj_res = await db.execute(
        select(CustomObjectDefinition).where(
            and_(CustomObjectDefinition.tenant_id == tenant_id, CustomObjectDefinition.slug == "demo_asset")
        )
    )
    obj = obj_res.scalar_one_or_none()
    if not obj:
        obj = CustomObjectDefinition(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Demo Asset",
            slug="demo_asset",
            plural_name="Demo Assets",
            description="Seeded object for Phase 2 UI testing",
            icon="Box",
            color="#6366F1",
            label_field="name",
            is_system=False,
            is_active=True,
            show_in_nav=True,
            display_order=0,
            created_by=admin_user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(obj)
        await db.flush()

        fields = [
            CustomObjectField(
                id=str(uuid.uuid4()),
                object_id=obj.id,
                name="name",
                label="Name",
                field_type="text",
                config={},
                is_required=True,
                is_unique=False,
                show_in_list=True,
                show_in_detail=True,
                is_searchable=True,
                display_order=0,
                placeholder="Asset name",
                help_text=None,
                created_at=now,
            ),
            CustomObjectField(
                id=str(uuid.uuid4()),
                object_id=obj.id,
                name="value",
                label="Value",
                field_type="number",
                config={},
                is_required=False,
                is_unique=False,
                show_in_list=True,
                show_in_detail=True,
                is_searchable=False,
                display_order=1,
                placeholder=None,
                help_text=None,
                created_at=now,
            ),
        ]
        db.add_all(fields)

        db.add(
            CustomObjectRecord(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                object_id=obj.id,
                data={"name": "Seeded Asset", "value": 123},
                display_label="Seeded Asset",
                owner_id=admin_user_id,
                created_at=now,
                updated_at=now,
            )
        )
