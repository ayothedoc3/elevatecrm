# MongoDB -> PostgreSQL Migration Status (Elev8 CRM)

This repo historically used **MongoDB** (Motor) with collections spread across `backend/server_mongo.py` and `backend/app/api/*`.
The production-facing backend is now **PostgreSQL + SQLAlchemy (async)** with the frontend API contract kept stable.

## Current state (this branch)

**Postgres-backed entrypoint:**
- `elevatecrm/backend/server.py`
- Routers: `elevatecrm/backend/app/api_pg/*`
- Models: `elevatecrm/backend/app/pg_models/models.py`
- Alembic: `elevatecrm/backend/alembic/*`
  - `elevatecrm/backend/alembic/versions/0001_init_core.py`
  - `elevatecrm/backend/alembic/versions/0002_phase2_modules.py`

**Legacy Mongo server kept for reference only:**
- `elevatecrm/backend/server_mongo.py`

## Phase 1 (Done): Core CRM

**Tables implemented (Phase 1 core):**
- `tenants`, `users`
- `accounts`, `contacts`, `leads`
- `pipelines`, `pipeline_stages`, `deals`
- `tasks`, `outreach_activities`, `timeline_events`
- `deal_handoffs`
- `calculation_definitions`, `calculation_results`
- `partners`, `products`

**Endpoints implemented (Phase 1 core):**
- Auth: `/api/auth/*`
- Workspaces (tenant-as-workspace): `/api/workspaces*`
- Leads: `/api/leads*`
- Deals: `/api/deals*` (stage gating + overrides + handoff)
- Pipelines: `/api/pipelines*` (kanban)
- Tasks: `/api/tasks*`
- Outreach/Activity: `/api/outreach*` + `/api/timeline*`
- Calculator: `/api/calculations*`
- Forecast: `/api/forecast/summary`

## Phase 2 (Done): Remaining modules migrated from Mongo

**Tables implemented (Phase 2 modules):**
- Landing Pages: `landing_pages`, `landing_page_versions`, `landing_page_events`, `landing_page_conversations`, `landing_page_generations`
- Inbox: `conversations`, `messages`
- Campaigns/Lists: `campaigns`, `lists`, `list_members`
- Affiliates: `affiliate_programs`, `affiliates`, `affiliate_links`, `affiliate_events`, `affiliate_commissions`, `affiliate_notifications`, `affiliate_settings`, `marketing_materials`
- Settings: `workspace_settings`, `workspace_integrations`, `ai_usage_configs`, `ai_usage_logs`, `settings_audit_logs`
- Workflows: `workflows`, `workflow_runs`, `workflow_blueprints`
- Custom Objects: `custom_object_definitions`, `custom_object_fields`, `custom_object_records`
- Blueprints: `crm_blueprints`

**Endpoints implemented (Phase 2 modules):**
- Landing Pages: `/api/landing-pages*` (+ public view endpoint)
- Inbox: `/api/inbox*`
- Lists: `/api/lists*`
- Campaigns: `/api/campaigns*`
- Affiliates (admin): `/api/affiliates*`
- Affiliate Portal (public): `/api/affiliate-portal*`
- Materials: `/api/materials*`
- Settings: `/api/settings*`
- Workflows: `/api/workflows*`
- Custom Objects: `/api/custom-objects*`
- Workflow Blueprints: `/api/blueprints*`
- Storage: `/api/storage/files/*`
- Referral redirect: `/api/ref/*`

## Not yet migrated (intentionally gated)

- Forms: `/api/forms*` and `/api/public/forms*` are still legacy-only and not included in `backend/server.py` yet.
  - The frontend keeps Forms hidden until Phase 3 (see `elevatecrm/frontend/src/App.js`).

## Testing

- Phase 1 core QA: `elevatecrm/PHASE1_CORE_TESTING.md`
- Phase 2 modules QA: `elevatecrm/PHASE2_MODULES_TESTING.md`
