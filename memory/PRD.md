# Elev8 CRM — Requirements & Workflow Specification

## 1. Purpose & Scope

The CRM must support all Elev8 sales motions, align fully with Playbooks 1, 2, and 3, and enable predictable execution, clean forecasting, and scalable partner sales.

The CRM must support:
- **Partnership Sales** (selling Elev8 services)
- **Partner Sales** (selling partner products)
- Call Center fast-cycle sales motions
- Enterprise and SMB sales motions
- Universal KPI tracking and forecasting
- Product-agnostic lead scoring

---

## 2. Core CRM Design Principles

- One CRM system for all sales motions
- Single source of truth for pipeline, KPIs, and forecasting
- Sales flow must mirror Elev8 playbooks exactly
- Mandatory data enforcement before stage progression
- Automation supports discipline, not workarounds
- Product-agnostic logic with partner-specific parameters

Every deal must clearly indicate:
- **Sales Motion Type** (Partnership Sales or Partner Sales)
- If Partner Sales: which partner the deal belongs to

---

## 3. Entity Model (Minimum Required Objects)

| Entity | Description |
|--------|-------------|
| Lead | Unqualified prospect |
| Contact | Individual person |
| Company / Account | Organization |
| Deal / Opportunity | Sales opportunity |
| Partner | For Partner Sales only |
| Product | Linked to Partner where applicable |

Every Deal must be linked to:
- One Company
- One primary Contact
- One Sales Motion Type
- Optionally one Partner
- One Product or Service Package

---

## 4. Sales Motion Identification (Mandatory)

Each Lead and Deal must include a **required field**:

### Sales Motion Type
- **Partnership Sales** (Elev8 services)
- **Partner Sales** (partner product)

If Partner Sales is selected:
- Partner Name (required)
- Partner Product (required)

This field controls:
- Pipeline routing
- Scripts
- KPIs
- Forecasting logic
- Reporting segmentation

---

## 5. Pipelines & Stages

The CRM must support multiple pipelines, all mapped to the universal Elev8 pipeline stages defined in Playbook 1.

### 5.1 Pipeline A — Qualification Pipeline

**Purpose:** Activate, contact, and qualify leads.

**Stages:**
1. New / Assigned
2. Working (Contact Attempts)
3. Info Collected
4. Unresponsive
5. Disqualified
6. Qualified → Push to Sales Pipeline

**Rules:**
- Leads must enter Working immediately after assignment
- Minimum number of touchpoints required before Unresponsive
- Info Collected requires all minimum qualification and scoring fields

### 5.2 Pipeline B — Sales Pipeline

**Purpose:** Convert qualified leads into revenue.

**Stages:**
1. Calculations / Analysis In Progress
2. Discovery / Demo Scheduled
3. Discovery / Demo Completed
4. Decision Pending
5. Trial / Pilot (if applicable)
6. Verbal Commitment
7. Closed Won
8. Closed Lost
9. Handoff to Delivery

**Rules:**
- Stage progression blocked if required fields are missing
- Demo cannot be scheduled without completed calculations
- Verbal Commitment requires completed discovery/demo
- No-show returns deal to Working or Discovery
- Every active deal must always have a next step scheduled

---

## 6. Lead Scoring (Universal & Mandatory)

Lead Scoring must be implemented as a **universal, product-agnostic system**.
The score represents strategic priority, not just likelihood to close.

Each Lead and Deal must display:
- **Lead Score** (0–100)
- **Lead Tier** (A–D)

### 6.1 Lead Scoring Categories & Weights

| Category | Weight |
|----------|--------|
| Size & Economic Impact | 30 |
| Urgency & Willingness to Act | 20 |
| Lead Source Quality | 15 |
| Strategic Motivation & Vision | 20 |
| Decision Readiness | 15 |
| **Total** | **100** |

### 6.2 Scoring Inputs (Required Fields)

- Economic Units (product-specific, e.g. locations, sites, licenses)
- Usage Volume (product-specific, e.g. fryers, users, lines)
- Urgency (1–5)
- Trigger Event
- Lead Source (auto-filled)
- Primary Motivation
- Decision Role
- Decision Process Clarity

> ⚠️ No additional questionnaire is allowed.

### 6.3 Automatic Lead Tiers

| Score Range | Tier | Description |
|-------------|------|-------------|
| 0–39 | D | Low priority, nurture only, excluded from forecast |
| 40–59 | C | Standard SDR motion |
| 60–79 | B | Strategic SDR or AE motion |
| 80–100 | A | Priority account, senior ownership |

Lead Tier controls:
- Owner assignment
- Script selection
- Forecast probability
- Dashboard visibility

### 6.4 Forecasting Logic

Weighted pipeline value must be calculated automatically:

```
Weighted Value = Estimated Deal Size × Tier Probability
```

**Default probabilities:**
| Tier | Probability |
|------|-------------|
| A | 60–80% |
| B | 35–60% |
| C | 15–30% |
| D | 0% |

Forecast views must be filterable by:
- Sales Motion Type
- Partner
- Lead Tier
- Product
- Owner

---

## 7. Required Fields & Enforcement by Stage

Each pipeline stage must enforce minimum required fields before progression.

**Examples:**
- Qualification requires scoring fields completed
- Discovery requires SPICED summary
- Proposal requires pricing and scope fields
- Closing requires confirmed decision process
- Handoff requires full documentation pack

> ⚠️ Stage regression must occur automatically if required data changes.

---

## 8. CRM Tasks, SLAs & Discipline

**Mandatory rules:**
- Task created after every sales interaction
- Follow-up SLAs enforced per stage
- Speed-to-lead SLA configurable per source
- No deal may remain without activity beyond defined SLA

Task completion and SLA compliance must be tracked as KPIs.

---

## 9. Ownership & Role Logic

### Primary Deal Owner:
- **SDR / Sales Specialist** during qualification
- **AE / Partnership Seller** during active sales

### Supporting Roles:
- **Sales Manager:** review, coaching, forecasting
- **Sales Coordinator:** pipeline hygiene, task enforcement
- **Sales Advisor:** approvals, diagnostics, system oversight

> Ownership changes must be logged automatically.

---

## 10. KPIs & Reporting

The CRM must support KPI tracking aligned with Playbook 1.

**Required KPI categories:**
- Outreach & activity
- Qualification & discovery
- Conversion & close rates
- Pipeline health
- Forecast accuracy
- SLA compliance
- CRM hygiene

**KPIs must be viewable:**
- By role
- By sales motion
- By partner
- By lead tier

---

## 11. Handoff to Delivery

Closed Won deals must trigger a mandatory handoff process.

### Required artifacts:
- SPICED summary
- Gap analysis
- Proposal
- Contract
- Risk notes
- Kickoff readiness checklist

### Handoff must:
- Assign delivery owner
- Schedule kickoff
- Lock sales stages
- Timestamp completion

---

## 12. Partner-Specific Configuration

For Partner Sales, the CRM must support:
- Partner-specific pipelines mapped to universal stages
- Partner-specific required fields
- Partner-specific KPIs
- Partner-specific compliance rules

> Core CRM logic must remain unchanged.

---

## 13. Governance & Change Control

| Playbook | Scope |
|----------|-------|
| Playbook 1 | Defines universal standards |
| Playbook 2 | Defines Partnership Sales execution |
| Playbook 3 | Defines partner-specific overrides |

CRM configuration must reflect this hierarchy.

---

## Implementation Phases

### Week 1 (Foundation) ✅
- Core entity models (Lead, Contact, Company, Deal, Partner, Product)
- Sales Motion Type logic
- Dual-pipeline architecture

### Week 2 (Lead Scoring & Qualification) ✅
- Lead scoring formula implementation
- Automatic tiering (A-D)
- Qualification Pipeline UI

### Week 3 (Sales Pipeline & SPICED) ✅
- Sales Pipeline implementation
- Stage-progression rules
- Mandatory SPICED summary enforcement

### Week 4 (KPIs & Forecasting) ✅
- Forecasting logic
- KPI dashboards
- Reporting views

### Post-Week 4 Features ✅ (Completed January 2026)
- **AI Assistant (Elev8 AI Sales Assistant):**
  - Lead Intelligence with score breakdown
  - SPICED Summary drafting with AI
  - Stage Readiness Advisor
  - Deal Risk Analysis
  - Strict governance: AI is advisory only

- **Handoff to Delivery:**
  - Backend: Full handoff workflow, artifact tracking, delivery owner assignment
  - Frontend: HandoffPage.js with two-panel layout, artifact management

- **Partner-specific Configurations:**
  - Backend: Partner pipeline/field/KPI/compliance configurations
  - Frontend: PartnerConfigPage.js with KPIs, Pipeline, Fields, Compliance tabs

- **SLA & Task Management:**
  - Backend: Task CRUD, SLA configuration, compliance tracking
  - Frontend: TasksPage.js with My Tasks, All Tasks, SLA Monitor tabs

---

## Test Credentials

- **Admin User:** `admin@demo.com` / `admin123`
