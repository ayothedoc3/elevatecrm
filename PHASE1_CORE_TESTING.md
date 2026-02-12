# Elev8 CRM - Phase 1 ("Core") End-to-End Test Script (PostgreSQL)

This is a **manual QA script** to verify Phase 1 is usable end-to-end for the core motion:
**Lead -> Assign -> Scoring -> Qualify -> Push to Sales -> Work Deal (next step + stage gating) -> Close -> Handoff -> Forecast**

## 0) Prereqs

- Node.js 18+ / 20+
- Python 3.10+ / 3.11+
- PostgreSQL 14+ running and reachable from this machine
  - Docker option:
    - `docker run --rm -e POSTGRES_USER=crm_user -e POSTGRES_PASSWORD=crm_password -e POSTGRES_DB=crm_os -p 5432:5432 postgres:16`
- Backend `.env` configured:
  - File: `elevatecrm/backend/.env`
  - If missing, copy from: `elevatecrm/backend/.env.example`
  - Ensure `DATABASE_URL` points to your Postgres (example):
    - `DATABASE_URL=postgresql://crm_user:crm_password@localhost:5432/crm_os`
  - Ensure backend port matches frontend env (default in this repo is `8001`)
- Frontend `.env` configured:
  - File: `elevatecrm/frontend/.env`
  - If missing, copy from: `elevatecrm/frontend/.env.example`
  - Ensure `REACT_APP_BACKEND_URL` points to the backend (default: `http://localhost:8001`)

## 1) First-time setup (schema)

1. Start Postgres and ensure the database in `DATABASE_URL` exists.
2. Run migrations:
   - `cd elevatecrm/backend`
   - `alembic upgrade head`

Note: `python server.py` will also attempt to create tables on startup (dev convenience), but **migrations are recommended**.

## 2) Reset demo data (clean run)

1. Stop backend + frontend.
2. Reset the demo tenant in Postgres:
   - `cd elevatecrm/backend`
   - `python reset_demo_pg.py`
3. Start backend (it will reseed demo data on startup if missing):
   - `cd elevatecrm/backend`
   - `python server.py`
4. Start frontend:
   - `cd elevatecrm/frontend`
   - `npm start`

Expected:
- Backend: `http://localhost:8001/api/health` returns healthy JSON.
- Frontend: `http://localhost:3000` loads.

## 3) Login (demo tenant)

Use tenant slug: `demo`

Credentials:
- Admin: `admin@demo.com` / `admin123`
- Manager: `manager@demo.com` / `manager123`
- Sales: `sales@demo.com` / `sales123`

Expected:
- You land in the app with navigation working.

## 4) Lead -> Assign -> Working (Qualification discipline)

1. Go to `Leads`.
2. Click `+ New Lead`.
3. Create a lead with:
   - First/Last name
   - Company name (so we can validate Account linking)
   - Sales Motion Type: `Partnership Sales`
4. Open the lead detail sheet.
5. In `Workflow`:
   - Select an Owner (Sales user)
   - Click `Assign`

Expected:
- Lead owner is set.
- Lead status automatically becomes `working`.

## 5) Lead Scoring (mandatory inputs; no extra questionnaire)

1. In the lead sheet, open `Scoring Inputs`.
2. Fill the required fields:
   - Economic Units
   - Usage Volume
   - Urgency (1-5)
   - Decision Process Clarity (1-5)
   - Trigger Event
   - Primary Motivation
   - Decision Role
3. Click `Save Score`.

Expected:
- Lead `score (0-100)` updates.
- Lead tier updates automatically (A/B/C/D).

## 6) Touchpoints -> Unresponsive gating (min 3)

1. In the lead sheet `Workflow`, use the `Touchpoints` section:
   - Log 1 touchpoint

Expected (SLA UI):
- Speed-to-lead shows a minutes value (and stops increasing after first touchpoint is logged).
- Cadence shows hours since last touchpoint (updates after each touchpoint).
2. Try to change Status to `Unresponsive` and click `Save Changes`.

Expected:
- Save is blocked with an error stating **at least 3 touchpoints** required.

3. Log 2 more touchpoints (total 3).
4. Set Status to `Unresponsive` and `Save Changes`.

Expected:
- Status save succeeds.
- Touchpoint count increments and "Last" timestamp updates.

## 7) Qualify -> Push to Sales (creates Contact + Deal + Next Step task)

1. Set Status to `Qualified` and `Save Changes`.
2. Click `Push to Sales`.
3. Provide:
   - Deal name (optional)
   - Amount
   - Next step date/time (**required**)
   - Next step note (optional)
4. Confirm push.

Expected:
- Lead is converted (removed from active Lead workflow).
- A Contact is created (or reused) for the deal.
- An Account is created/upserted from Company name and linked.
- A Deal is created in the Sales Pipeline.
- A **Next Step task** exists for the deal (open).

## 8) Deal discipline: Contact required + Next step required

1. Go to `Pipeline`.
2. Open the new deal.

Expected (Details tab):
- Contact shows and is editable (required).
- Next Step shows (required) and can be updated.
- Lead Tier + Lead Score display on the deal.

## 9) Tasks panel (Next Step task + manual tasks)

1. Open the deal `Tasks` tab.

Expected:
- You see an open task with badge `Next Step` (kind = next_step).

2. Create a manual task:
   - Click `New`
   - Title + Due date/time
   - Create

Expected:
- Manual task appears in the list.

3. Mark the manual task `Complete`.

Expected:
- Task disappears from open list (status becomes completed).

## 10) Activity logging rotates Next Step tasks

1. Open `Activity` tab.
2. Click `Log Activity`.
3. Log an outbound call (any notes).
4. Return to `Tasks`.

Expected:
- There is still an open `Next Step` task (previous next-step tasks are completed and a fresh one is created).

## 11) Stage gating: "Demo Scheduled" requires completed calculation

1. Drag the deal from `Calculations / Analysis In Progress` -> `Discovery / Demo Scheduled`.

Expected:
- Move is blocked with a message about the calculation being required (unless overridden by admin/manager with reason).

2. Open the deal `Calculator` tab.
3. Fill required calculator inputs and `Save`.
4. Open the deal `Demo` tab.
5. Set `Scheduled At` and click `Save Demo`.
6. Drag to `Discovery / Demo Scheduled` again.

Expected:
- Move succeeds (no override required).

## 12) Stage gating: "Demo Completed" requires Demo completion + SPICED

1. Drag the deal from `Discovery / Demo Scheduled` -> `Discovery / Demo Completed`.

Expected:
- Move is blocked until:
  - Demo is marked completed, and
  - SPICED summary is complete.

2. Open the deal `SPICED` tab and fill all fields. Click `Save SPICED`.
3. Open the deal `Demo` tab and either:
   - Set Status = `Completed` and click `Save Demo`, or
   - Set `Completed At` and click `Save Demo`.
4. Drag to `Discovery / Demo Completed` again.

Expected:
- Move succeeds (no override required).

## 13) Close Won / Lost locks stages by default

1. Drag deal to `Closed Won`.

Expected:
- Deal status becomes `won`.
- Stage changes back to open stages are blocked unless you use admin override.

2. (Optional) Try dragging `Closed Won` -> an open stage.

Expected:
- Blocked with "Deal is closed..." message (override allowed for admin/manager).

## 14) Handoff to Delivery gating (must be completed)

1. After `Closed Won`, try to drag the deal into `Handoff to Delivery`.

Expected:
- Blocked until handoff packet is complete.

2. Open the deal `Handoff` tab and complete:
   - Delivery Owner (required)
   - Kickoff Scheduled (required)
   - All checklist items (required)
3. Click `Save Handoff`.
4. Drag deal to `Handoff to Delivery`.

Expected:
- Stage move succeeds.

## 15) Forecast (weighted pipeline + SLA risk)

1. Go to `Reports` -> `Forecast`.
2. Verify totals:
   - Pipeline Value
   - Weighted Forecast
   - Deals Count
   - Missing Next Steps / Overdue Next Steps
   - Stale Deals (no activity >= N days)
3. Change filters and confirm results update:
   - Motion type (Partner Sales vs Partnership Sales)
   - Tier A/B/C/D
   - Owner
   - Partner/Product (only when Motion = Partner Sales)

Expected:
- Totals and tier breakdown update as filters change.

## 16) Partner Sales variant (required partner + product)

1. Create a new Lead with Sales Motion Type = `Partner Sales`.
2. Provide Partner + Product (required in the lead form).
3. Push to Sales.
4. In `Reports` -> `Forecast`, set Motion = `Partner Sales` and filter by Partner/Product.

Expected:
- Partner/Product values are present and filterable in Forecast.

## 16) CSV Import/Export (HubSpot migration helpers)

### 16.1 Contacts CSV

1. Go to `Contacts`.
2. Click `Export` and confirm a `.csv` downloads successfully.
3. Click `Import`, upload the same CSV (or a modified one with a new email), and run the import.

Expected:
- Import returns a summary: `created`, `updated`, `skipped`, and (if any) `errors`.
- Imported contacts appear in the Contacts list.

### 16.2 Leads CSV

1. Go to `Leads`.
2. Click `Export` and confirm a `.csv` downloads successfully.
3. Click `Import`, upload the exported CSV (or a modified one), and run the import.

Expected:
- Import returns a summary: `created`, `updated`, `skipped`, and (if any) `errors`.
- Imported leads appear in the Leads list.

Notes:
- Minimum required per row: `Email` or `Phone`.
- If you include scoring input columns, Lead Score/Tier will be auto-computed.

## 17) KPI endpoint (server-side summary)

1. Go to `Reports`.
2. Open browser devtools Network tab and refresh Reports.

Expected:
- The frontend calls `GET /api/kpis/summary?time_range=...` and receives `200`.
- Reports load without client-side KPI aggregation logic.

## 18) Partner default pipeline routing (optional)

1. Login as Admin or Manager.
2. Go to `Settings` -> `Workspace` -> `Partner Pipelines`.
3. For a partner, choose a `Default Pipeline` (or click `Clone Default & Assign`).
4. Create a `Partner Sales` lead for that partner + product and `Push to Sales`.
5. Go to `Pipeline` and select the partner’s pipeline from the pipeline dropdown.

Expected:
- The pushed deal is created in the partner’s default pipeline when no explicit pipeline is selected during push.
