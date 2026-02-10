# Elev8 CRM - Phase 2 ("Modules") Manual QA Script (PostgreSQL)

This is a manual QA script to verify the Phase 2 modules are usable on the PostgreSQL backend:
Landing Pages, Inbox, Lists, Campaigns, Affiliates (+ Affiliate Portal), Settings, Workflows, Custom Objects, Blueprints.

## 0) Prereqs

- Node.js 18+ / 20+
- Python 3.10+ / 3.11+
- PostgreSQL 14+ running and reachable from this machine
  - Docker option:
    - `docker run --rm -e POSTGRES_USER=crm_user -e POSTGRES_PASSWORD=crm_password -e POSTGRES_DB=crm_os -p 5432:5432 postgres:16`

## 1) First-time setup (schema)

1. Configure backend env:
   - `elevatecrm/backend/.env` (copy from `elevatecrm/backend/.env.example` if needed)
   - Ensure `DATABASE_URL` points to your Postgres.
2. Run migrations:
   - `cd elevatecrm/backend`
   - `alembic upgrade head`

## 2) Reset demo data (recommended)

This ensures Phase 2 demo rows exist (landing page, inbox message, affiliate portal user, etc.).

- Stop backend + frontend
- `cd elevatecrm/backend`
- `python reset_demo_pg.py`
- Start backend:
  - `python server.py`
- Start frontend:
  - `cd elevatecrm/frontend`
  - Copy `elevatecrm/frontend/.env.example` to `elevatecrm/frontend/.env`
  - `npm start`

Expected:
- Backend health: `http://localhost:8001/api/health`
- Frontend: `http://localhost:3000`

## 3) Login (demo tenant)

Tenant slug: `demo`

Credentials:
- Admin: `admin@demo.com` / `admin123`
- Manager: `manager@demo.com` / `manager123`
- Sales: `sales@demo.com` / `sales123`

## 4) Landing Pages (AI Page Builder)

1. Navigate to `AI Page Builder`.
2. Verify you see a seeded page `Demo Offer Page` (slug `demo-offer`).
3. Open the page builder and make a simple edit, save.
4. Publish it (or Unpublish/Publish) and confirm status changes.
5. Test public render:
   - `http://localhost:3000/pages/demo-offer`

Optional (requires AI provider configured in Settings):
- Use `Generate` and/or `Chat` in the builder and confirm a new version/schema is saved.

## 5) Inbox

1. Navigate to `Inbox`.
2. Verify you see a seeded conversation `Welcome to Elevate CRM`.
3. Open it and send a message (UI action).

Expected:
- Message list updates
- Conversation `last_message_preview`, counts, and timestamps update

## 6) Lists

1. Navigate to `Lists`.
2. Verify seeded `Demo List` exists.
3. Create a new list, edit it, and delete it.

## 7) Campaigns

1. Navigate to `Campaigns`.
2. Verify seeded `Demo Email Campaign` exists.
3. Create a new campaign linked to a list.
4. Duplicate the campaign.
5. Use `Send` (this backend simulates send and updates counters).

Expected:
- Stats/overview endpoints respond and counters update.

## 8) Affiliates (Admin)

1. Navigate to `Affiliates`.
2. Verify there is a seeded program `Demo Affiliate Program`.
3. Verify a seeded affiliate exists (email `affiliate@demo.com`).

## 9) Affiliate Portal (Public)

Seeded affiliate portal user:
- Email: `affiliate@demo.com`
- Password: `affiliate123`
- Tenant slug: `demo`

1. Visit `http://localhost:3000/affiliate-portal/login`
2. Login with the seeded credentials.
3. Generate a new affiliate link (or view existing).

Referral redirect test (seeded referral code):
- Open: `http://localhost:8001/api/ref/DEMOAFF1`

Expected:
- Redirects to the landing page URL and appends `?ref=DEMOAFF1`
- Increments `click_count` for the link and logs an affiliate event.

## 10) Settings

1. Navigate to `Settings`.
2. Update workspace name/color/timezone and save.
3. View AI settings and usage.

Optional:
- Add an integration provider + API key and click `Test` (depends on real provider credentials).

## 11) Workflows

1. Navigate to `Workflows`.
2. Verify `Demo Follow-up Workflow` exists.
3. Create/edit a workflow, toggle status, and delete.

## 12) Custom Objects

1. Navigate to `Objects`.
2. Verify the seeded object `Demo Asset` exists.
3. Open it and verify you can list/create/update/delete records.

## 13) Blueprints

1. Navigate to `Blueprints`.
2. Verify CRM blueprints load from `/api/workspaces/blueprints`.
3. Verify Workflow blueprints load from `/api/blueprints`.

