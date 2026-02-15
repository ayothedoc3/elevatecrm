# Elev8 CRM - Phase 1 ("Core") End-to-End Test Script (PostgreSQL)

This is a **manual QA script** to verify Phase 1 is usable end-to-end for the core motion:
**Lead -> Assign -> Scoring -> Qualify -> Push to Sales -> Work Deal (next step + stage gating) -> Close -> Handoff -> Forecast**

This QA script is run against the deployed Railway environment (no local setup required).

## 2) Reset demo data (clean run) - do this BEFORE QA starts

This script assumes a clean `demo` tenant state so every rep is testing the same baseline.

Reset is typically done by an admin/ops user with Railway access.

**Railway (recommended)**
1. Open the backend service in Railway.
2. Run the demo reset script in the backend container:
   - `cd backend && python reset_demo_pg.py`
3. Restart/redeploy the backend service (demo data is seeded on startup).

If you cannot reset, ask an admin/ops owner to reset the `demo` tenant and then begin QA at **Section 3 (Login)**.

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

## 19) Click-through UX: Dashboard + Notifications

1. Go to `Dashboard`.
2. Click each KPI card:
   - `Total Contacts` -> goes to Contacts
   - `Active Deals` / `Pipeline Value` -> goes to Pipeline
   - `Deals Won` -> goes to Reports
3. In `Recent Deals`, click a deal row.

Expected:
- Clicking a deal opens the deal detail (Pipeline page with the deal sheet open).

4. Click the notification bell (top-right).
5. Click a **Task** notification and a **Recent Activity** notification.

Expected:
- Clicking a notification takes you to the related record:
  - Deal notifications -> open the deal sheet
  - Contact notifications -> open the contact sheet
  - Otherwise -> opens Activity

## 20) Discord integration (Admin UI)

1. Login as `Admin`.
2. Go to `Settings` -> `Integrations`.
3. Under `Communications`, find `Discord` and click `Add Webhook`.
4. Paste a Discord webhook URL (created in your Discord channel settings).
5. Click `Test Connection`.

Expected:
- A confirmation message posts to the Discord channel.

6. Click `Save Integration`.

Expected:
- Discord shows as `Configured` in Integrations.

7. Trigger Discord alerts:
   - Assign a Lead to a user (lead assignment alert)
   - Move a Deal to `Closed Won` (win alert)
   - Move a Deal to `Closed Lost` (loss alert)

Expected:
- Each event posts a message to the Discord channel.

## 21) @Mentions -> mention tasks + clickable notifications

1. In any Deal, set/update a field that supports notes (example: `Next Step Note`) and include a mention like `@sales` or `@manager`.
2. Save.
3. Login as the mentioned user.
4. Click the notification bell and click the `Mention` task.

Expected:
- A `Mention` task exists and is clickable.
- Clicking it opens the related deal.

## 22) Sidebar grouped navigation (scanability by role)

1. Open the left sidebar.
2. Verify sections are grouped with headers:
   - `Sales CRM`
   - `Marketing & AI`
   - `Operations`
3. Verify links are under the expected group:
   - Sales: Dashboard, Contacts, Leads, Pipeline, Activity, Reports, Affiliates
   - Marketing: AI Page Builder, Lists, Campaigns
   - Operations: Inbox, Workflows, Objects, Blueprints
4. Collapse and expand the sidebar.

Expected:
- Grouping remains clear when expanded and navigation still works when collapsed.

## 23) Landing page tile visual previews

1. Go to `AI Page Builder` / `Landing Pages`.
2. Confirm each page tile shows a mini visual preview (screenshot-style render), not a plain color block.
3. Create a new page (quick create or AI create), then return to the grid.
4. Confirm the new page tile shows its own preview and page name.

Expected:
- Every tile displays a visual page preview derived from that page content.
- Tile actions (Preview, Edit, Publish/Unpublish, Copy URL, Delete) continue to work.

## 24) AI Landing Page Creator (Create with AI)

1. Open `AI Page Builder` / `Landing Pages` and click `Create with AI`.
2. Generate a page from prompt inputs.
3. Save the page, then reopen it in the builder.
4. Modify content in chat (or section editor), save, and publish.
5. Click `View Live` / open `/pages/{slug}`.

Expected:
- AI-generated content persists after save.
- Edits made after creation are reflected in builder and live page.
- Publish state toggles correctly and slug URL resolves.

## 25) Settings SLA controls and live enforcement

1. Login as Admin.
2. Go to `Settings` -> `Workspace`.
3. Update SLA values:
   - `speed_to_lead_minutes`
   - `lead_cadence_hours`
   - `deal_cadence_hours`
4. Save settings.
5. Return to Leads and Pipeline views.

Expected:
- SLA values are persisted.
- Speed-to-lead and cadence breach indicators reflect the updated thresholds.
