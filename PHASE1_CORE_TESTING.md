# Elev8 CRM — Phase 1 End-to-End QA Script

**Core motion under test:**
Lead → Assign → Score → Qualify → Push to Sales → Work Deal (next step + stage gating) → Close → Handoff → Forecast

**Environment:** Deployed Railway app (no local setup required).
**URL:** `https://frontend-production-9a2f.up.railway.app`

---

## 1) Login

**Tenant slug:** `demo`

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@demo.com` | `admin123` |
| Manager | `manager@demo.com` | `manager123` |
| Sales | `sales@demo.com` | `sales123` |

**Expected:** You land on the Dashboard with sidebar navigation visible.

---

## 2) Create a Lead and assign an Owner

1. Go to **Leads**.
2. Click **+ New Lead**.
3. Fill in:
   - First name / Last name
   - Company name
   - Owner (select a Sales user from the dropdown)
   - Sales Motion Type: `Partnership Sales`
4. Click **Create Lead**.

**Expected:**
- Lead appears in the list.
- Owner is set to the selected user.
- Status is automatically `working` (because an owner was assigned on creation).

> **Alternative:** You can also create the lead without an owner, then open the lead detail → Workflow section → select Owner → click **Assign**. The status will change to `working` on assignment.

---

## 3) Lead Scoring

1. Open the lead detail sheet.
2. Scroll to **Scoring Inputs** and fill in all required fields:
   - Economic Units
   - Usage Volume
   - Urgency (1–5)
   - Decision Process Clarity (1–5)
   - Trigger Event
   - Primary Motivation
   - Decision Role
3. Click **Compute Score**.

**Expected:**
- Lead score updates (0–100).
- Lead tier updates automatically (A / B / C / D).

---

## 4) Touchpoints and Unresponsive gating

1. In the lead detail → **Workflow** → **Touchpoints** section, log **1 touchpoint**.

**Expected (SLA indicators):**
- Speed-to-lead badge shows elapsed minutes since creation (stops increasing after the first touchpoint).
- Cadence badge shows hours since last touchpoint.

2. Change Status to `Unresponsive` and click **Save Changes**.

**Expected:**
- Save is **blocked** with an error: at least 3 touchpoints required.

3. Log **2 more touchpoints** (total: 3).
4. Change Status to `Unresponsive` and click **Save Changes**.

**Expected:**
- Status saves successfully.
- Touchpoint count and "Last touchpoint" timestamp both update.

---

## 5) Qualify and Push to Sales

1. Change Status to `Qualified` and click **Save Changes**.
2. Click **Push to Sales**.
3. Fill in:
   - Deal name (optional)
   - Amount
   - Next step date/time (**required**)
   - Next step note (optional)
4. Confirm the push.

**Expected:**
- Lead is marked as converted.
- A **Contact** is created (or reused if email matches).
- An **Account** is created (or upserted from the company name).
- A **Deal** is created in the Sales Pipeline at the first stage.
- A **Next Step task** (kind = `next_step`) is created for the deal.

---

## 6) Deal detail: Contact + Next Step + Lead data

1. Go to **Pipeline**.
2. Open the deal that was just created.

**Expected (Details tab):**
- Contact is shown and editable.
- Next Step is shown with date/time and note (editable).
- Lead Tier and Lead Score are displayed on the deal.

---

## 7) Tasks panel

1. Open the deal **Tasks** tab.

**Expected:**
- An open task with a `Next Step` badge is visible.

2. Click **New** to create a manual task (title + due date). Click **Create**.

**Expected:**
- The manual task appears in the list.

3. Mark the manual task as **Complete**.

**Expected:**
- The task disappears from the open list.

---

## 8) Activity logging rotates Next Step tasks

1. Open the deal **Activity** tab.
2. Click **Log Activity** and log an outbound call with notes.
3. Return to the **Tasks** tab.

**Expected:**
- The previous Next Step task is marked completed.
- A **new** Next Step task has been created automatically.

---

## 9) Stage gating: "Demo Scheduled" requires calculation

1. Drag the deal from `Calculations / Analysis In Progress` → `Discovery / Demo Scheduled`.

**Expected:**
- Move is **blocked** with a message that the calculation must be completed first.
- Admin/manager can override by providing a reason.

2. Open the deal → **Calculator** tab → fill required inputs → click **Save**.
3. Open the deal → **Demo** tab → set **Scheduled At** → click **Save Demo**.
4. Drag the deal to `Discovery / Demo Scheduled` again.

**Expected:**
- Move succeeds without override.

---

## 10) Stage gating: "Demo Completed" requires Demo + SPICED

1. Drag the deal from `Discovery / Demo Scheduled` → `Discovery / Demo Completed`.

**Expected:**
- Move is **blocked** until both conditions are met:
  - Demo is marked completed.
  - SPICED summary is filled out.

2. Open the deal → **SPICED** tab → fill all fields → click **Save SPICED**.
3. Open the deal → **Demo** tab → set Status to `Completed` (or set `Completed At`) → click **Save Demo**.
4. Drag the deal to `Discovery / Demo Completed` again.

**Expected:**
- Move succeeds without override.

---

## 11) Close Won / Lost locks stages

1. Drag the deal to `Closed Won`.

**Expected:**
- Deal status becomes `won`.
- Dragging back to an open stage is **blocked** ("Deal is closed...").
- Admin/manager can override with a reason.

---

## 12) Handoff to Delivery

1. After Closed Won, drag the deal to `Handoff to Delivery`.

**Expected:**
- Move is **blocked** until the handoff packet is complete.

2. Open the deal → **Handoff** tab and complete:
   - Delivery Owner (required)
   - Kickoff Scheduled (required)
   - All checklist items checked (SPICED summary, gap analysis, proposal, contract, risk notes, kickoff readiness)
3. Click **Save Handoff**.
4. Drag the deal to `Handoff to Delivery`.

**Expected:**
- Stage move succeeds.

---

## 13) Forecast

1. Go to **Reports** → **Forecast** tab.
2. Verify totals:
   - Pipeline Value
   - Weighted Forecast (tier-based probability)
   - Deals Count
   - Missing Next Steps / Overdue Next Steps
   - Stale Deals (no activity beyond threshold)
3. Change filters and confirm results update:
   - Motion type (Partnership Sales / Partner Sales)
   - Tier (A / B / C / D)
   - Owner
   - Partner / Product (visible when Motion = Partner Sales)

**Expected:**
- Totals and tier breakdown update as filters change.

---

## 14) Partner Sales variant

1. Create a new Lead with Sales Motion Type = `Partner Sales`.
2. Fill in Partner Name and Partner Product (both required for Partner Sales).
3. Push to Sales.
4. In **Reports** → **Forecast**, filter by Motion = `Partner Sales` and select the partner/product.

**Expected:**
- Partner and Product values are present on the deal and filterable in Forecast.

---

## 15) CSV Import / Export

### 15a) Contacts CSV

1. Go to **Contacts**.
2. Click **Export** — confirm a `.csv` downloads.
3. Click **Import** — upload the same CSV (or a modified one with a new email).

**Expected:**
- Import returns a summary: created, updated, skipped, errors.
- Imported contacts appear in the list.

### 15b) Leads CSV

1. Go to **Leads**.
2. Click **Export** — confirm a `.csv` downloads.
3. Click **Import** — upload the exported CSV (or a modified one).

**Expected:**
- Import returns a summary: created, updated, skipped, errors.
- Imported leads appear in the list.
- If scoring input columns are included, Lead Score/Tier is auto-computed.

---

## 16) KPI endpoint

1. Go to **Reports**.
2. Open browser DevTools → Network tab and refresh.

**Expected:**
- The frontend calls `GET /api/kpis/summary?time_range=...` and receives `200`.
- KPIs are computed server-side (not aggregated client-side).

---

## 17) Partner default pipeline routing

> **Prerequisite:** You must have created at least one Partner Sales lead (Step 14) so that a partner exists in the system.

1. Login as Admin or Manager.
2. Go to **Settings** → **Workspace** → scroll down to **Partner Pipelines**.
3. For a partner, choose a Default Pipeline from the dropdown (or click **Clone Default & Assign**).
4. Create a new `Partner Sales` lead for that partner and Push to Sales.
5. Go to **Pipeline** and select the partner's pipeline from the pipeline dropdown.

**Expected:**
- The deal was created in the partner's default pipeline (not the workspace default).

---

## 18) Dashboard click-through and notifications

1. Go to **Dashboard**.
2. Click each KPI card:
   - `Total Contacts` → navigates to Contacts
   - `Active Deals` / `Pipeline Value` → navigates to Pipeline
   - `Deals Won` → navigates to Reports
3. In **Recent Deals**, click a deal row.

**Expected:**
- Clicking a deal opens the Pipeline page with that deal's detail sheet open.

4. Click the **notification bell** (top-right).
5. Click a task notification and an activity notification.

**Expected:**
- Deal notifications → open the deal detail sheet.
- Contact notifications → open the contact detail sheet.
- Other notifications → open the Activity page.

---

## 19) Discord integration

1. Login as Admin.
2. Go to **Settings** → **Integrations**.
3. Under **Communications**, find Discord and click **Add Webhook**.
4. Paste a Discord webhook URL (from your Discord channel settings → Integrations → Webhooks).
5. Click **Test Connection**.

**Expected:**
- A test message posts to the Discord channel.

6. Click **Save Integration**.

**Expected:**
- Discord shows as `Configured`.

7. Trigger alerts by performing these actions:
   - Assign a Lead to a user → lead assignment alert fires.
   - Move a Deal to `Closed Won` → win alert fires.
   - Move a Deal to `Closed Lost` → loss alert fires.

**Expected:**
- Each event posts a message to the Discord channel.

---

## 20) @Mentions

1. Open any Deal and update a notes field (e.g. Next Step Note) with a mention: `@sales` or `@manager`.
2. Save.
3. Login as the mentioned user.
4. Click the notification bell → click the **Mention** task.

**Expected:**
- A task with kind `mention` exists for the mentioned user.
- Clicking it navigates to the related deal.

---

## 21) Sidebar grouped navigation

1. Open the left sidebar (expand if collapsed).
2. Verify three section headers are visible:
   - **Sales CRM** — Dashboard, Contacts, Leads, Pipeline, Activity, Reports, Affiliates
   - **Marketing & AI** — AI Page Builder, Lists, Campaigns
   - **Operations** — Inbox, Workflows, Objects, Blueprints
3. Collapse the sidebar.

**Expected:**
- Section grouping is clear when expanded.
- Navigation still works when collapsed.

---

## 22) Landing page tile previews

1. Go to **AI Page Builder**.
2. Confirm each page tile shows a mini visual preview (not a plain color block).
3. Create a new page, then return to the grid.

**Expected:**
- The new tile shows a visual preview derived from the page content.
- Tile actions (Preview, Edit, Publish/Unpublish, Copy URL, Delete) all work.

---

## 23) AI Landing Page Creator

1. In **AI Page Builder**, click **Create with AI**.
2. Generate a page from the prompt inputs.
3. Save the page, then reopen it in the builder.
4. Edit content, save, and publish.
5. Open the live page via the slug URL.

**Expected:**
- AI-generated content persists after save.
- Edits are reflected in the builder and on the live page.
- Publish/unpublish toggles correctly.

---

## 24) SLA settings

1. Login as Admin.
2. Go to **Settings** → **Workspace** → scroll to **Sales SLAs**.
3. Update the three thresholds:
   - Speed-to-Lead (minutes)
   - Lead Cadence (hours)
   - Deal Cadence (hours)
4. Click **Save Changes**.
5. Return to Leads and Pipeline.

**Expected:**
- SLA values persist after save.
- Speed-to-lead and cadence breach indicators on leads and deals reflect the updated thresholds.
