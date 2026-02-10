# Elev8 CRM - Build Plan (Playbooks 1-3)

## 1) Goal
Build a single CRM that supports **all Elev8 sales motions** (Partnership Sales, Partner Sales, Call Center, SMB/Enterprise) with:
- **Playbook-perfect execution** (stages match the playbooks)
- **Mandatory data enforcement** before stage progression
- **Universal lead scoring (0-100) + tiering (A-D)** that is product-agnostic
- **Predictable forecasting** (weighted pipeline) and hygiene/SLA discipline
- **Partner-specific overrides** without changing core logic

## 2) Guiding Principles (Non-Negotiables)
1. One CRM for all motions (no "special pipelines" that break reporting).
2. Single source of truth for pipeline, KPIs, and forecast.
3. Stage movement is **blocked** when required data is missing (override is audited).
4. Automations support discipline (no silent bypasses).
5. Product-agnostic core with partner-specific parameters and rule overlays.

## 3) Phase Summary

### Phase 0 - Stabilize & Align (Foundation)
**Outcome:** Core app is internally reliable; API/UI contracts match; security baseline is sane.
- Align frontend <-> backend API contracts (remove/replace stubs).
- Standardize auth + RBAC checks for sensitive actions.
- Add configuration for environments (secrets, CORS, ports, logging).
- Create a minimal test harness + smoke tests for critical flows.

**Exit criteria**
- Login works; Leads + Pipeline + Stage moves work without 4xx mismatches.
- No simulated "send" paths on core sales flows.
- Secrets are not hard-coded; CORS isn't wildcard in production.

---

### Phase 1 - Sales Core MVP (Go-Live for Sales)
**Outcome:** Sales team can run the full motion **end-to-end** for Qualification -> Sales -> Close -> Handoff.

#### Phase 1 scope (must-have)
**A) Data model (minimum required objects)**
- Lead
- Contact
- Company / Account (minimum viable)
- Deal / Opportunity
- Partner (for Partner Sales)
- Product (linked to Partner where applicable)
- Tasks + SLAs (for discipline)

**B) Mandatory Sales Motion Identification**
On **every Lead and Deal**:
- `sales_motion_type` (required): `partnership_sales` | `partner_sales`
- If `partner_sales`:
  - `partner_id` (required)
  - `product_id` (required)

**C) Pipelines & Stages (Playbook 1 universal taxonomy)**
Two primary pipelines (can be duplicated per partner but mapped to the same universal stages):
- **Pipeline A - Qualification**
  - New / Assigned
  - Working (Contact Attempts)
  - Info Collected
  - Unresponsive
  - Disqualified
  - Qualified -> Push to Sales Pipeline
- **Pipeline B - Sales**
  - Calculations / Analysis In Progress
  - Discovery / Demo Scheduled
  - Discovery / Demo Completed
  - Decision Pending
  - Trial / Pilot (optional)
  - Verbal Commitment
  - Closed Won
  - Closed Lost
  - Handoff to Delivery

**D) Enforcement (required fields by stage)**
- Stage progression blocked when required fields are missing.
- Admin override requires reason + is logged.
- "Every active deal must have a next step scheduled" enforced for active Sales stages.

**E) Universal Lead Scoring (no extra questionnaires)**
Implement required scoring inputs and compute:
- `lead_score` (0-100)
- `lead_tier` (A-D)
Weights:
- Size & Economic Impact (30)
- Urgency & Willingness to Act (20)
- Lead Source Quality (15)
- Strategic Motivation & Vision (20)
- Decision Readiness (15)

**F) Forecasting**
Weighted pipeline value:
`estimated_deal_size * tier_probability`
Default tier probability bands:
- A: 0.60-0.80
- B: 0.35-0.60
- C: 0.15-0.30
- D: 0.00

Forecast views filterable by:
- sales motion type
- partner
- tier
- product
- owner

**G) Handoff to Delivery**
Closed Won triggers a required handoff checklist + delivery owner assignment + kickoff scheduling.

#### Phase 1 "Definition of Done" (acceptance)
- SDR can create/assign leads, complete scoring inputs, and progress Qualification stages with enforcement.
- AE can progress Sales stages with enforcement and required "next step".
- Managers can view pipeline health + weighted forecast, filter by motion/partner/tier/product/owner.
- Closed Won produces a handoff packet and locks sales stages.
- Overrides are role-restricted and fully audited.
- QA script: `PHASE1_CORE_TESTING.md`

---

### Phase 2 - Execution Layer (Comms + Automations)
**Outcome:** Replace GHL operational execution where it matters most.
- Two-way inbox (SMS/email) with Twilio/SendGrid/Mailgun and inbound webhooks.
- Automation engine: triggers -> conditions -> actions (create task, send SMS/email, update fields).
- Activity capture (calls/meetings), templates, snippets.
- Speed-to-lead + SLA automation (alerts, escalations).

---

### Phase 3 - Partner Sales Overrides (Playbook 3)
**Outcome:** Scale partner sales without forking the core CRM.
- Partner-specific required fields and rules (overlays).
- Partner-specific KPIs and pipeline variants mapped to universal stages.
- Product catalogs, pricing, and quoting hooks.

---

### Phase 4 - Scale & Enterprise (Hardening + Admin)
**Outcome:** Multi-team, multi-tenant reliability.
- Fine-grained permissions, audit export, data retention/GDPR tooling.
- Data import/export, dedupe, enrichment.
- Advanced reporting + cohorting + forecast accuracy.
- Observability, backups, migrations, and deployment pipelines.

## 4) Work Breakdown (Epics)

### Epic 1 - Canonical Data Model
- Add Sales Motion fields to Lead/Deal
- Add Partner + Product objects
- Add Company object and enforce Deal->Company + Deal->Primary Contact
- Add task + SLA objects
- Migration/backfill for existing records

### Epic 2 - Pipeline Engine (Stages + Rules)
- Create universal stage taxonomy + mapping
- Store stage rules (required fields, SLA rules, next-step rules)
- Block moves when rules fail
- Override path (admin-only) with reason + audit log
- Regression logic when required fields become missing

### Epic 3 - Universal Scoring
- Persist required scoring inputs
- Deterministic scoring computation (weights)
- Tier assignment + tier-based routing/visibility

### Epic 4 - Forecasting + KPI Layer
- Weighted pipeline calculations
- Forecast snapshots (daily/weekly)
- KPI rollups by role/motion/partner/tier/product/owner

### Epic 5 - Handoff to Delivery
- Handoff checklist object + required artifacts
- Delivery owner assignment + kickoff scheduling placeholder
- Stage locking + timestamps

### Epic 6 - Platform Hardening
- Secrets management + env config
- CORS restrictions + rate limiting
- Audit log completeness for ownership changes + overrides
- Smoke tests + CI

## 5) Implementation Order (Recommended)
1. **Phase 0:** Fix API contract mismatches and remove critical stubs (pipeline stage move + calculations + auth).
2. **Phase 1:** Add sales motion + partner/product + universal pipelines + enforcement.
3. Add scoring engine + tier routing.
4. Add tasks/SLAs + next-step enforcement.
5. Add weighted forecast + KPI views.
6. Add handoff to delivery.

## 6) Risks / Notes
- Current codebase mixes multiple backend approaches; Phase 0 must pick and standardize the runtime backend.
- "Simulated" comms/campaign features must be clearly marked and excluded from go-live until integrated.
- Partner-specific overrides should be implemented as overlays to prevent core logic drift.
