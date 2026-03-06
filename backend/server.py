"""Elevate CRM API (PostgreSQL version).

This is the production-facing entrypoint. The legacy MongoDB server is kept in
`server_mongo.py` for reference/fallback during migration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from sqlalchemy import select
from starlette.middleware.cors import CORSMiddleware

from app.core.database import AsyncSessionLocal, engine, init_db
from app.pg_models import models as _models  # noqa: F401 (register metadata)
from app.pg_models.models import Tenant

from app.api_pg.services import run_crm_automations
from app.api_pg.seed import seed_demo_data


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def _run_crm_automation_cycle() -> None:
    async with AsyncSessionLocal() as read_session:
        tenant_ids = list((await read_session.execute(select(Tenant.id))).scalars().all())

    for tenant_id in tenant_ids:
        async with AsyncSessionLocal() as tenant_session:
            try:
                await run_crm_automations(
                    tenant_session,
                    tenant_id=tenant_id,
                    actor_id=None,
                    actor_name="Scheduler",
                )
                await tenant_session.commit()
            except Exception:
                await tenant_session.rollback()
                logger.exception("Failed CRM automation cycle for tenant %s", tenant_id)


async def _crm_automation_scheduler(stop_event: asyncio.Event, interval_seconds: int) -> None:
    interval = max(60, int(interval_seconds or 300))
    while not stop_event.is_set():
        try:
            await _run_crm_automation_cycle()
        except Exception:
            logger.exception("CRM automation scheduler cycle failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Elevate CRM (PostgreSQL)...")
    await init_db()

    async with AsyncSessionLocal() as session:
        await seed_demo_data(session)
        await session.commit()

    scheduler_enabled = (os.getenv("CRM_AUTOMATION_SCHEDULER_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"})
    scheduler_interval = int(os.getenv("CRM_AUTOMATION_INTERVAL_SECONDS", "300"))
    scheduler_stop = asyncio.Event()
    scheduler_task: asyncio.Task | None = None
    if scheduler_enabled:
        scheduler_task = asyncio.create_task(_crm_automation_scheduler(scheduler_stop, scheduler_interval))
        logger.info("CRM automation scheduler started (interval=%ss)", max(60, scheduler_interval))

    yield

    if scheduler_task:
        scheduler_stop.set()
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task

    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Elevate CRM API",
    description="Elev8 CRM backend API (PostgreSQL)",
    version="2.0.0",
    lifespan=lifespan,
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


cors_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # If allow_origins is ["*"], credentials must be False per the CORS spec.
    allow_credentials=cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# Phase 1 core (Postgres-backed) routers
from app.api_pg.auth_routes import router as auth_router  # noqa: E402
from app.api_pg.accounts_routes import router as accounts_router  # noqa: E402
from app.api_pg.calculations_routes import router as calculations_router  # noqa: E402
from app.api_pg.contacts_routes import router as contacts_router  # noqa: E402
from app.api_pg.deals_routes import router as deals_router  # noqa: E402
from app.api_pg.forecast_routes import router as forecast_router  # noqa: E402
from app.api_pg.leads_routes import router as leads_router  # noqa: E402
from app.api_pg.outreach_routes import router as outreach_router  # noqa: E402
from app.api_pg.partners_products_routes import router as partners_products_router  # noqa: E402
from app.api_pg.pipelines_routes import router as pipelines_router  # noqa: E402
from app.api_pg.tasks_routes import router as tasks_router  # noqa: E402
from app.api_pg.timeline_routes import router as timeline_router  # noqa: E402
from app.api_pg.workspaces_routes import router as workspaces_router  # noqa: E402
from app.api_pg.landing_pages_routes import router as landing_pages_router  # noqa: E402
from app.api_pg.inbox_routes import router as inbox_router  # noqa: E402
from app.api_pg.lists_routes import router as lists_router  # noqa: E402
from app.api_pg.campaigns_routes import router as campaigns_router  # noqa: E402
from app.api_pg.affiliates_routes import router as affiliates_router  # noqa: E402
from app.api_pg.materials_routes import router as materials_router  # noqa: E402
from app.api_pg.affiliate_portal_routes import router as affiliate_portal_router  # noqa: E402
from app.api_pg.settings_routes import router as settings_router  # noqa: E402
from app.api_pg.workflows_routes import router as workflows_router  # noqa: E402
from app.api_pg.custom_objects_routes import router as custom_objects_router  # noqa: E402
from app.api_pg.blueprints_routes import router as blueprints_router  # noqa: E402
from app.api_pg.kpis_routes import router as kpis_router  # noqa: E402
from app.api_pg.storage_routes import router as storage_router  # noqa: E402
from app.api_pg.referral_routes import router as referral_router  # noqa: E402
from app.api_pg.public_forms_routes import router as public_forms_router  # noqa: E402
from app.api_pg.webhooks_routes import router as webhooks_router  # noqa: E402

api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(leads_router)
api_router.include_router(contacts_router)
api_router.include_router(accounts_router)
api_router.include_router(partners_products_router)
api_router.include_router(pipelines_router)
api_router.include_router(deals_router)
api_router.include_router(tasks_router)
api_router.include_router(outreach_router)
api_router.include_router(calculations_router)
api_router.include_router(timeline_router)
api_router.include_router(forecast_router)
api_router.include_router(landing_pages_router)
api_router.include_router(inbox_router)
api_router.include_router(lists_router)
api_router.include_router(campaigns_router)
api_router.include_router(affiliates_router)
api_router.include_router(materials_router)
api_router.include_router(affiliate_portal_router)
api_router.include_router(settings_router)
api_router.include_router(workflows_router)
api_router.include_router(custom_objects_router)
api_router.include_router(blueprints_router)
api_router.include_router(kpis_router)
api_router.include_router(storage_router)
api_router.include_router(referral_router)
api_router.include_router(public_forms_router)
api_router.include_router(webhooks_router)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host=host, port=port)
