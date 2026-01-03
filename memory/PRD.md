# Elev8 CRM - Product Requirements Document (PRD)

## Executive Summary

Elev8 CRM is a comprehensive multi-CRM platform supporting multiple sales motions, intelligent lead scoring, and scalable partner sales. This document serves as the primary source of truth for AI agents and developers continuing work on this platform.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Completed Features](#completed-features)
4. [In Progress Features](#in-progress-features)
5. [Future Roadmap](#future-roadmap)
6. [API Reference](#api-reference)
7. [Testing Guide](#testing-guide)
8. [Troubleshooting](#troubleshooting)

---

## System Overview

### Purpose
The CRM supports:
- **Partnership Sales**: Selling Elev8 services directly
- **Partner Sales**: Selling partner products (e.g., Frylow oil management)
- **Call Center fast-cycle sales motions**
- **Enterprise and SMB sales motions**
- **Universal KPI tracking and forecasting**
- **Product-agnostic lead scoring**

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python 3.11)
- **Database**: MongoDB
- **Authentication**: JWT-based auth

### Credentials
- **Admin**: `admin@demo.com` / `admin123`
- **Affiliate Portal**: `sarah@affiliate.com` / `affiliate123`

---

## Architecture

### Directory Structure

```
/app
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── elev8_routes.py      # Lead, Partner, Product, Company APIs
│   │   │   ├── settings_routes.py   # Settings & BYOK APIs
│   │   │   ├── affiliate_routes.py  # Affiliate management
│   │   │   └── landing_pages_routes.py
│   │   ├── services/
│   │   │   ├── encryption_service.py   # AES-256 key encryption
│   │   │   ├── settings_service.py     # Workspace settings
│   │   │   └── unified_ai_service.py   # AI service layer
│   │   ├── migrations/
│   │   │   └── elev8_pipelines.py      # Pipeline configuration
│   │   └── db/
│   │       └── mongodb.py
│   └── server.py
├── frontend/
│   └── src/
│       └── pages/
│           ├── LeadsPage.js       # Lead management UI
│           ├── PartnersPage.js    # Partner management UI
│           ├── SettingsPage.js    # Settings UI
│           └── ...
└── memory/
    └── PRD.md                     # This file
```

### Database Collections

| Collection | Purpose |
|------------|---------|
| `leads` | Lead records with scoring |
| `partners` | Partner Sales partners |
| `products` | Products linked to partners |
| `companies` | Organization records |
| `contacts` | Contact records |
| `deals` | Deals/Opportunities |
| `pipelines` | Pipeline configurations |
| `pipeline_stages` | Pipeline stage definitions |
| `workspace_settings` | Workspace configuration |
| `workspace_integrations` | Encrypted API keys |
| `ai_usage_configs` | AI provider settings |
| `settings_audit_logs` | Audit trail |

---

## Completed Features

### ✅ Phase 1: Settings Module (Complete)

**Backend:**
- Encryption service (AES-256) for API key storage
- Settings service for workspace configuration
- AI provider management (OpenAI, Claude, OpenRouter)
- Integration management (Twilio, SendGrid, Stripe)
- Audit logging for all key operations

**Frontend:**
- Settings page with 5 tabs (Workspace, AI, Integrations, Affiliates, Security)
- Secure key input with masked display
- Test connection functionality

**API Endpoints:**
- `GET/PUT /api/settings/workspace`
- `GET/PUT /api/settings/ai`
- `GET/POST/DELETE /api/settings/integrations`
- `GET /api/settings/providers`
- `GET /api/settings/audit-logs`

### ✅ Phase 2: Entity Model (Complete)

**Entities Implemented:**
1. **Lead** - With full scoring system
2. **Partner** - For Partner Sales motion
3. **Product** - Linked to partners
4. **Company** - Organization records

**Lead Scoring System:**
- Score: 0-100 based on 5 weighted categories
- Tiers: A (80-100), B (60-79), C (40-59), D (0-39)
- Automatic tier assignment
- Forecast probability by tier

**Dual Pipeline Structure:**
- Qualification Pipeline (6 stages)
- Sales Pipeline (9 stages)

**API Endpoints (prefix: /api/elev8):**
- `GET/POST /leads` - Lead CRUD
- `POST /leads/{id}/qualify` - Lead → Deal conversion
- `GET/POST /partners` - Partner CRUD
- `GET/POST /products` - Product CRUD
- `GET/POST /companies` - Company CRUD
- `POST /setup/pipelines` - Initialize pipelines
- `GET /pipelines/elev8` - Get pipeline config

### ✅ Phase 3: Frontend Pages (Complete)

- **LeadsPage.js** - Lead management with scoring visualization
- **PartnersPage.js** - Partner and product management

---

## In Progress Features

### 🔄 Pipeline Page Integration

**Status:** Partially Complete

**What's Done:**
- Dual pipeline backend structure
- Pipeline setup endpoint

**What's Needed:**
- Update existing PipelinePage.js to show both pipelines
- Add pipeline switcher (Qualification vs Sales)
- Stage progression validation

### 🔄 Deal Enhancement

**Status:** Partially Complete

**What's Done:**
- Deal created with sales_motion_type
- SPICED fields on deal model

**What's Needed:**
- SPICED summary editor on deal detail
- Stage-based required field enforcement
- Discovery stage SPICED validation

---

## Future Roadmap

### Phase 4: KPIs & Reporting

**Spec Reference:** Section 10

**Requirements:**
1. **Outreach & Activity KPIs**
   - Calls made, emails sent
   - Response rates
   - Speed-to-lead metrics

2. **Qualification & Discovery KPIs**
   - Qualification rate
   - Discovery completion rate
   - SPICED completion rate

3. **Conversion & Close Rates**
   - Stage conversion rates
   - Win/loss by tier
   - Average deal cycle time

4. **Pipeline Health**
   - Pipeline velocity
   - Weighted pipeline value
   - Stage aging alerts

5. **Forecast Accuracy**
   - Predicted vs actual
   - Tier accuracy analysis

6. **SLA Compliance**
   - Follow-up SLA adherence
   - Stage timeout alerts

**Implementation Priority:**
- [ ] Create `/api/elev8/kpis` endpoint
- [ ] Build KPI dashboard component
- [ ] Add drill-down by sales motion, partner, tier

### Phase 5: SLA & Task Management

**Spec Reference:** Section 8

**Requirements:**
- Task created after every sales interaction
- Follow-up SLAs enforced per stage
- Speed-to-lead SLA configurable per source
- No deal without activity beyond SLA

**Implementation:**
- [ ] Create `tasks` collection
- [ ] Task API endpoints
- [ ] SLA configuration in settings
- [ ] Overdue task alerts

### Phase 6: Handoff to Delivery

**Spec Reference:** Section 11

**Requirements:**
- Mandatory handoff process for Closed Won
- Required artifacts:
  - SPICED summary
  - Gap analysis
  - Proposal
  - Contract
  - Risk notes
  - Kickoff readiness checklist

**Implementation:**
- [ ] Handoff workflow trigger
- [ ] Checklist component
- [ ] Delivery team assignment
- [ ] Kickoff scheduling

### Phase 7: Partner-Specific Configuration

**Spec Reference:** Section 12

**Requirements:**
- Partner-specific pipelines mapped to universal stages
- Partner-specific required fields
- Partner-specific KPIs
- Partner-specific compliance rules

**Implementation:**
- [ ] Enhance Partner entity with configuration JSON
- [ ] Dynamic required fields based on partner
- [ ] Partner KPI dashboards

---

## API Reference

### Authentication

All API calls require Bearer token:
```
Authorization: Bearer <token>
```

Get token:
```bash
curl -X POST "$API_URL/api/auth/login?tenant_slug=demo" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}'
```

### Elev8 CRM APIs

#### Leads

```bash
# List leads
GET /api/elev8/leads?page=1&page_size=20&tier=A&status=new

# Create lead
POST /api/elev8/leads
{
  "first_name": "John",
  "last_name": "Smith",
  "email": "john@company.com",
  "company_name": "Acme Corp",
  "sales_motion_type": "partnership_sales",  # or "partner_sales"
  "partner_id": "uuid",  # required if partner_sales
  "product_id": "uuid",  # required if partner_sales
  "economic_units": 25,
  "usage_volume": 50,
  "urgency": 4,
  "trigger_event": "Rising costs in Q4",
  "primary_motivation": "cost_reduction",
  "decision_role": "decision_maker",
  "decision_process_clarity": 4
}

# Qualify lead (creates Deal, Contact, Company)
POST /api/elev8/leads/{id}/qualify
```

#### Partners

```bash
# List partners
GET /api/elev8/partners

# Create partner
POST /api/elev8/partners
{
  "name": "Frylow",
  "partner_type": "strategic",
  "status": "active",
  "description": "Oil management system partner",
  "territory": "North America"
}
```

#### Products

```bash
# List products
GET /api/elev8/products?partner_id={id}

# Create product
POST /api/elev8/products
{
  "name": "Oil Extender",
  "partner_id": "uuid",
  "description": "Extends fryer oil life",
  "base_price": 2500,
  "economic_unit_label": "fryers",
  "usage_volume_label": "oil_gallons_per_week"
}
```

#### Pipeline Setup

```bash
# Initialize Elev8 pipelines (run once)
POST /api/elev8/setup/pipelines

# Get pipeline configuration
GET /api/elev8/pipelines/elev8
```

### Settings APIs

```bash
# Workspace settings
GET/PUT /api/settings/workspace

# AI configuration
GET/PUT /api/settings/ai

# Integrations (keys are encrypted, never returned)
GET /api/settings/integrations
POST /api/settings/integrations
{
  "provider_type": "openai",
  "api_key": "sk-..."
}

# Test connection
POST /api/settings/integrations/test
{
  "provider_type": "openai",
  "api_key": "sk-..."  # optional, uses stored key if not provided
}
```

---

## Testing Guide

### Backend Testing

```bash
# Get auth token
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login?tenant_slug=demo" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))")

# Test leads API
curl -s -X GET "$API_URL/api/elev8/leads" -H "Authorization: Bearer $TOKEN"

# Test lead scoring (create lead and check score)
curl -s -X POST "$API_URL/api/elev8/leads" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "Lead",
    "sales_motion_type": "partnership_sales",
    "economic_units": 50,
    "usage_volume": 100,
    "urgency": 5,
    "decision_role": "decision_maker",
    "decision_process_clarity": 5
  }'
```

### Frontend Testing

1. Login at http://localhost:3000/login
2. Navigate to Leads page - verify tier badges and scores
3. Create a new lead - verify scoring calculation
4. Navigate to Partners page - create partner and products
5. Create Partner Sales lead - verify partner/product required

### Lead Scoring Verification

| Input | Expected Score Range | Expected Tier |
|-------|---------------------|---------------|
| High everything (50 units, 5 urgency, decision_maker, referral, cost_reduction) | 80-100 | A |
| Medium (15 units, 3 urgency, champion) | 60-79 | B |
| Low (5 units, 2 urgency, user) | 40-59 | C |
| Minimal data | 0-39 | D |

---

## Troubleshooting

### Common Issues

#### 1. "Sales pipeline not configured"
**Solution:** Run pipeline setup endpoint:
```bash
POST /api/elev8/setup/pipelines
```

#### 2. "Partner ID is required for Partner Sales motion"
**Solution:** Create partner and product first, then include their IDs when creating Partner Sales lead.

#### 3. Lead score not updating
**Solution:** Lead score recalculates when updating scoring fields:
- economic_units, usage_volume, urgency, trigger_event
- primary_motivation, decision_role, decision_process_clarity, source

#### 4. Cannot qualify lead
**Solution:** Ensure required fields are filled:
- economic_units
- usage_volume
- urgency
- decision_role

### Logs

```bash
# Backend logs
tail -100 /var/log/supervisor/backend.err.log

# Frontend logs
tail -100 /var/log/supervisor/frontend.out.log
```

---

## For AI Agents

### Key Files to Review

1. `/app/backend/app/api/elev8_routes.py` - All entity APIs
2. `/app/backend/app/migrations/elev8_pipelines.py` - Pipeline definitions
3. `/app/frontend/src/pages/LeadsPage.js` - Lead management UI
4. `/app/frontend/src/pages/PartnersPage.js` - Partner management UI

### Implementation Guidelines

1. **Lead Scoring:** All changes to scoring must update `calculate_lead_score()` function
2. **Sales Motion:** Always validate partner_id/product_id for partner_sales
3. **Pipelines:** Use pipeline_type field ("qualification" or "sales") to distinguish
4. **Security:** Never expose API keys - always use encryption service

### Next Tasks (Priority Order)

1. **Update PipelinePage.js** - Show both pipelines with switcher
2. **SPICED Editor** - Add to deal detail view
3. **Stage Progression** - Implement required field validation
4. **KPI Dashboard** - Build reporting page

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-03 | Initial implementation - Entity Model, Lead Scoring, Dual Pipelines |
| 1.1 | 2026-01-03 | Settings Module with BYOK |
| 1.2 | 2026-01-03 | Frontend pages for Leads and Partners |

---

*Last Updated: 2026-01-03*
*Document Maintainer: AI Agent*
