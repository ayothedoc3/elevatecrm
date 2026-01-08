# Elev8 CRM - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Core Features](#core-features)
5. [API Reference](#api-reference)
6. [End-to-End Testing Guide](#end-to-end-testing-guide)
7. [Deployment Guide](#deployment-guide)
8. [External Integrations](#external-integrations)
9. [Security & Governance](#security--governance)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Elev8 CRM is a comprehensive, multi-pipeline Customer Relationship Management system designed for B2B sales organizations. It supports multiple sales motions, enforces sales discipline through mandatory data collection, and provides AI-assisted selling capabilities.

### Key Capabilities
- **Dual-Pipeline Architecture**: Separate Qualification and Sales pipelines
- **Universal Lead Scoring**: Product-agnostic scoring with automatic tiering (A-D)
- **AI Sales Assistant**: Advisory-only AI for SPICED drafting and lead intelligence
- **Partner Sales Support**: Partner-specific configurations, KPIs, and compliance rules
- **SLA & Task Management**: Automated SLA tracking with breach detection
- **KPI Dashboards**: Real-time forecasting and performance metrics
- **Handoff to Delivery**: Structured workflow for Closed Won deals

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18 with Tailwind CSS & shadcn/ui
- **Database**: MongoDB
- **AI Integration**: OpenAI GPT-4o / Claude / Gemini (configurable)

---

## Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │  Leads   │ │ Pipeline │ │   KPIs   │ │ Partners │ │Settings││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
│                           AI Assistant Panel                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    /api/elev8/ Routes                       │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │ │
│  │  │  Leads  │ │Partners │ │Products │ │Companies│           │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │ │
│  │  │Pipelines│ │   KPIs  │ │ Handoff │ │  Tasks  │           │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │ │
│  │  ┌──────────────────┐ ┌──────────────────────┐             │ │
│  │  │   AI Assistant   │ │  Partner Config      │             │ │
│  │  │  (Advisory Only) │ │  (Custom Rules)      │             │ │
│  │  └──────────────────┘ └──────────────────────┘             │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Core Services                            │ │
│  │  Lead Scoring Engine │ Encryption Service │ Unified AI     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MongoDB                                   │
│  Collections: leads, deals, contacts, companies, partners,      │
│  products, pipelines, pipeline_stages, tasks, sla_configs,      │
│  deal_handoffs, partner_configs, activities, ai_assistant_logs  │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Module Structure
```
/app/backend/app/api/elev8/
├── __init__.py         # Main router combining all sub-routers
├── models.py           # Enums & Pydantic schemas
├── auth.py             # JWT authentication helper
├── scoring.py          # Deterministic lead scoring engine
├── leads.py            # Lead CRUD & qualification
├── partners.py         # Partner management
├── products.py         # Product catalog
├── companies.py        # Company/Account management
├── pipelines.py        # Pipeline setup & queries
├── ai_assistant.py     # AI Assistant (advisory/draft-only)
├── kpis.py             # KPIs & Forecasting
├── handoff.py          # Handoff to Delivery workflow
├── partner_config.py   # Partner-specific configurations
└── tasks.py            # Tasks & SLA management
```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 6.0+
- Yarn package manager

### Backend Setup
```bash
cd /app/backend
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd /app/frontend
yarn install
```

### Environment Variables

**Backend (.env)**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=elev8_crm
SECRET_KEY=your-secret-key-change-in-production
# Optional: AI Provider Keys (or use Settings UI)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Frontend (.env)**
```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

### Initialize Pipelines
After starting the backend, initialize the dual-pipeline structure:
```bash
curl -X POST "$API_URL/api/elev8/setup/pipelines" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Core Features

### 1. Dual-Pipeline System

**Qualification Pipeline** (for Leads)
| Stage | Purpose |
|-------|---------|
| New / Assigned | Fresh leads awaiting first contact |
| Working | Active outreach in progress |
| Info Collected | Basic qualification data gathered |
| Unresponsive | No response after defined touchpoints |
| Disqualified | Not a fit |
| Qualified | Ready to convert to Deal |

**Sales Pipeline** (for Deals)
| Stage | Purpose |
|-------|---------|
| Calculations / Analysis | Initial analysis phase |
| Discovery / Demo Scheduled | Meeting booked |
| Discovery / Demo Completed | SPICED required |
| Decision Pending | Awaiting buyer decision |
| Trial / Pilot | Product evaluation |
| Verbal Commitment | Verbal yes, pending paperwork |
| Closed Won | Deal closed successfully |
| Closed Lost | Deal lost |
| Handoff to Delivery | Post-sale handoff |

### 2. Lead Scoring System

Automatic scoring (0-100) based on 5 categories:

| Category | Weight | Inputs |
|----------|--------|--------|
| Size & Economic Impact | 30% | economic_units, usage_volume |
| Urgency & Willingness | 20% | urgency (1-5), trigger_event |
| Lead Source Quality | 15% | source type |
| Strategic Motivation | 20% | primary_motivation |
| Decision Readiness | 15% | decision_role, decision_process_clarity |

**Automatic Tier Assignment**
| Score | Tier | Description | Forecast Probability |
|-------|------|-------------|---------------------|
| 80-100 | A | Priority Account | 60-80% |
| 60-79 | B | Strategic Account | 35-60% |
| 40-59 | C | Standard Account | 15-30% |
| 0-39 | D | Nurture Only | 0% |

### 3. AI Assistant (Advisory Only)

**Governance Rules - AI CANNOT:**
- Change lead scores or tiers
- Move pipeline stages
- Modify deal ownership
- Auto-save any data
- Bypass validation rules

**AI CAN:**
- Draft SPICED summaries (user must save)
- Explain lead score breakdowns
- Suggest outreach messages
- Analyze deal risks (read-only)

### 4. Sales Motion Types

| Motion | Description |
|--------|-------------|
| Partnership Sales | Selling Elev8 services directly |
| Partner Sales | Selling partner products (requires partner_id, product_id) |

### 5. SPICED Framework

Required for Discovery stage progression:
- **S**ituation: Company background
- **P**ain: Business pain points
- **I**mpact: Quantified impact ($)
- **C**ritical Event: Timeline trigger
- **E**conomic: Budget, decision authority
- **D**ecision: Buying process, criteria

---

## API Reference

### Authentication
All endpoints require JWT Bearer token:
```
Authorization: Bearer <token>
```

Login:
```bash
POST /api/auth/login
Body: {"email": "admin@demo.com", "password": "admin123"}
Response: {"access_token": "...", "user": {...}}
```

### Lead Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/leads | List leads with filtering |
| POST | /api/elev8/leads | Create lead (auto-scores) |
| GET | /api/elev8/leads/{id} | Get lead details |
| PUT | /api/elev8/leads/{id} | Update lead (re-scores) |
| DELETE | /api/elev8/leads/{id} | Delete lead |
| POST | /api/elev8/leads/{id}/qualify | Convert to Deal |
| GET | /api/elev8/leads/{id}/score-breakdown | Get score details |
| GET | /api/elev8/leads/scoring/stats | Get tier distribution |

### Deal/Pipeline Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/pipelines/elev8 | Get dual-pipeline config |
| POST | /api/elev8/setup/pipelines | Initialize pipelines |
| GET | /api/deals | List deals |
| PUT | /api/deals/{id} | Update deal (including SPICED) |

### AI Assistant Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/ai-assistant/status | Check AI configuration |
| GET | /api/elev8/ai-assistant/governance | Get governance rules |
| POST | /api/elev8/ai-assistant/spiced/draft | Draft SPICED summary |
| GET | /api/elev8/ai-assistant/leads/{id}/score-explanation | Explain score |
| GET | /api/elev8/ai-assistant/leads/{id}/tier-explanation | Explain tier |
| POST | /api/elev8/ai-assistant/leads/{id}/outreach-draft | Draft outreach |
| GET | /api/elev8/ai-assistant/deals/{id}/stage-readiness | Stage analysis |
| GET | /api/elev8/ai-assistant/deals/{id}/risk-analysis | Risk factors |
| GET | /api/elev8/ai-assistant/pipeline/health-summary | Pipeline health |

### KPI & Forecasting Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/forecasting/summary | Weighted forecast |
| GET | /api/elev8/kpis/overview | KPI overview |
| GET | /api/elev8/kpis/sales-motion | KPIs by sales motion |
| GET | /api/elev8/kpis/leaderboard | Sales leaderboard |

### Task & SLA Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/tasks | List tasks |
| POST | /api/elev8/tasks | Create task |
| PUT | /api/elev8/tasks/{id} | Update task |
| POST | /api/elev8/tasks/{id}/complete | Complete task |
| GET | /api/elev8/tasks/my-tasks | Current user's tasks |
| GET | /api/elev8/sla/config | SLA configurations |
| POST | /api/elev8/sla/config | Create SLA (admin) |
| GET | /api/elev8/sla/status | SLA compliance status |

### Handoff Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/deals/{id}/handoff-status | Handoff readiness |
| POST | /api/elev8/deals/{id}/handoff/initiate | Start handoff |
| PUT | /api/elev8/deals/{id}/handoff/artifact | Update artifact |
| POST | /api/elev8/deals/{id}/handoff/complete | Complete handoff |
| GET | /api/elev8/handoffs | List handoffs |

### Partner Configuration Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/elev8/partners/{id}/config | Get partner config |
| PUT | /api/elev8/partners/{id}/config | Update config (admin) |
| GET | /api/elev8/partners/{id}/kpis | Partner KPIs |
| GET | /api/elev8/partners/{id}/compliance-check | Compliance check |
| GET | /api/elev8/config/fields-by-stage | Required fields |

---

## End-to-End Testing Guide

### Test Credentials
```
Email: admin@demo.com
Password: admin123
```

### Test Flow 1: Lead to Deal Conversion

```bash
# Set variables
API_URL="https://your-domain.com"
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}' \
  | jq -r '.access_token')

# 1. Create a lead
curl -X POST "$API_URL/api/elev8/leads" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "email": "john@acme.com",
    "company_name": "ACME Corp",
    "sales_motion_type": "partnership_sales",
    "economic_units": 25,
    "usage_volume": 50,
    "urgency": 4,
    "trigger_event": "Budget approved for Q1",
    "primary_motivation": "cost_reduction",
    "decision_role": "decision_maker",
    "decision_process_clarity": 4,
    "source": "referral"
  }'

# Expected: Lead created with score ~80+ (Tier A)

# 2. View score breakdown
curl "$API_URL/api/elev8/leads/{lead_id}/score-breakdown" \
  -H "Authorization: Bearer $TOKEN"

# 3. Qualify lead to deal
curl -X POST "$API_URL/api/elev8/leads/{lead_id}/qualify" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Deal created in Sales Pipeline at "Calculations/Analysis" stage
```

### Test Flow 2: AI Assistant SPICED Drafting

```bash
# 1. Open deal in UI at /pipeline
# 2. Click on deal card to open detail sheet
# 3. Click "AI Assistant - Draft SPICED" button
# 4. Go to SPICED tab
# 5. Enter context notes
# 6. Click "Generate SPICED Draft"
# 7. Click "Apply to Form" to pre-fill SPICED editor
# 8. Review and Save
```

### Test Flow 3: KPI Dashboard

```bash
# 1. Navigate to /kpis
# 2. Verify 4 summary cards (Pipeline Value, Weighted Forecast, Closed Won, Win Rate)
# 3. Check Forecast tab - tier breakdown
# 4. Check Activity KPIs tab - lead generation, deal performance
# 5. Check Pipeline Health tab - risk distribution
# 6. Check Leaderboard tab
# 7. Change period selector (Week/Month/Quarter)
```

### Test Flow 4: Task & SLA

```bash
# Create task
curl -X POST "$API_URL/api/elev8/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Follow up call",
    "task_type": "call",
    "priority": "high",
    "due_date": "2025-01-15T14:00:00Z",
    "deal_id": "{deal_id}"
  }'

# Check SLA status
curl "$API_URL/api/elev8/sla/status?entity_type=deals" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Shows compliant/at-risk/breached counts
```

### Test Flow 5: Handoff to Delivery

```bash
# 1. First, close a deal as Won
curl -X PUT "$API_URL/api/deals/{deal_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "won"}'

# 2. Check handoff status
curl "$API_URL/api/elev8/deals/{deal_id}/handoff-status" \
  -H "Authorization: Bearer $TOKEN"

# 3. Initiate handoff
curl -X POST "$API_URL/api/elev8/deals/{deal_id}/handoff/initiate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_owner_id": "{user_id}",
    "kickoff_date": "2025-01-20T10:00:00Z"
  }'

# 4. Add artifacts
curl -X PUT "$API_URL/api/elev8/deals/{deal_id}/handoff/artifact?artifact_type=gap_analysis" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Gap Analysis Document",
    "content": "Analysis content...",
    "completed": true
  }'

# 5. Complete handoff (after all required artifacts)
curl -X POST "$API_URL/api/elev8/deals/{deal_id}/handoff/complete" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Deployment Guide

### Deployment Readiness Assessment

| Category | Status | Notes |
|----------|--------|-------|
| Core CRM Features | ✅ Ready | All CRUD operations functional |
| Lead Scoring | ✅ Ready | Deterministic, server-side |
| Pipeline Management | ✅ Ready | Dual-pipeline working |
| AI Assistant | ✅ Ready | Governance enforced |
| KPI Dashboard | ✅ Ready | All metrics functional |
| Task Management | ✅ Ready | CRUD + SLA monitoring |
| Handoff Workflow | ✅ Ready | Full artifact management |
| Partner Config | ✅ Ready | Custom rules support |
| Authentication | ✅ Ready | JWT-based |
| Multi-tenancy | ✅ Ready | tenant_id on all records |

### Pre-Deployment Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Configure MongoDB connection string
- [ ] Set up SSL/TLS certificates
- [ ] Configure AI provider API keys (or use Settings UI)
- [ ] Set appropriate CORS origins
- [ ] Run pipeline initialization endpoint
- [ ] Create admin user
- [ ] Test all critical flows

### Recommended Infrastructure

```
Production:
- 2+ backend instances (load balanced)
- MongoDB replica set (3 nodes)
- Redis for session caching (optional)
- CDN for frontend assets

Minimum Requirements:
- 2 CPU cores
- 4GB RAM
- 20GB storage
```

---

## External Integrations

### Currently Integrated

| Integration | Status | Configuration |
|-------------|--------|---------------|
| **OpenAI (GPT-4o)** | ✅ Ready | Via Settings UI or env var |
| **Anthropic (Claude)** | ✅ Ready | Via Settings UI or env var |
| **Google (Gemini)** | ✅ Ready | Via Settings UI or env var |
| **Emergent LLM Key** | ✅ Ready | Universal key for AI providers |

### Integration-Ready (Requires Implementation)

| Integration | Purpose | Effort |
|-------------|---------|--------|
| **Twilio** | SMS notifications, SLA alerts | Low |
| **SendGrid/Mailgun** | Email notifications | Low |
| **Stripe** | Payment processing | Medium |
| **Slack** | Team notifications | Low |
| **Zapier/Make** | Workflow automation | Medium |
| **Salesforce** | Data sync | High |
| **HubSpot** | Marketing automation | Medium |
| **Calendly** | Meeting scheduling | Low |
| **DocuSign** | Contract signing | Medium |
| **Google Calendar** | Meeting sync | Low |

### Webhook Support

The system is designed to support webhooks for:
- Lead created/updated
- Deal stage changes
- Task due/overdue
- SLA breaches
- Handoff initiated/completed

### API Integration Points

```javascript
// Example: External system creating a lead
POST /api/elev8/leads
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@external.com",
  "source": "api_integration",
  "source_detail": "Partner Portal",
  "sales_motion_type": "partner_sales",
  "partner_id": "...",
  "product_id": "..."
}

// Example: CRM pushing deal updates to external system
// Implement webhook listener in your system:
// POST https://your-system.com/webhooks/elev8
// Body: { "event": "deal.stage_changed", "deal": {...} }
```

---

## Security & Governance

### Authentication
- JWT tokens with configurable expiration
- Secure password hashing (bcrypt)
- Role-based access control (admin, owner, user)

### Data Security
- API key encryption at rest (via encryption_service.py)
- MongoDB connection with authentication
- HTTPS enforced in production

### AI Governance (Critical)

**Hard Constraints - AI Cannot:**
1. Modify lead scores
2. Change pipeline stages
3. Update deal ownership
4. Auto-save any data
5. Bypass validation rules
6. Access cross-tenant data

**All AI outputs are:**
- Clearly marked as "AI Suggestion" or "Draft"
- Require explicit user action to save
- Logged for audit purposes

### Audit Logging
- All AI assistant requests logged
- Partner config changes logged
- Handoff activities logged
- Task completions logged

---

## Troubleshooting

### Common Issues

**1. Lead score not updating**
- Ensure scoring fields are provided: `economic_units`, `usage_volume`, `urgency`, etc.
- Score recalculates on lead update

**2. AI Assistant shows "Not Configured"**
- Go to Settings > AI & Intelligence
- Add at least one AI provider API key
- Or ensure `EMERGENT_LLM_KEY` is available

**3. Qualification fails**
- Check required fields: `economic_units`, `usage_volume`, `urgency`, `decision_role`
- Ensure Sales Pipeline exists (run setup endpoint)

**4. Handoff cannot complete**
- Verify deal status is "won"
- Ensure all required artifacts are marked complete
- Ensure SPICED summary exists

**5. SLA showing all breached**
- This is expected if `updated_at` is old
- Update deals to reset activity timestamp

### Logs
```bash
# Backend logs
tail -f /var/log/supervisor/backend.err.log

# Check MongoDB
mongosh --eval "db.leads.find().limit(1)"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2025 | Initial release with full PRD implementation |

---

## Support

For issues or questions:
1. Check this documentation
2. Review API error messages
3. Check backend logs
4. Contact support team

---

**Document Version:** 1.0.0  
**Last Updated:** January 2025  
**Author:** Elev8 Development Team
