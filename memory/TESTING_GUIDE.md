# Elev8 CRM - Quick Start Testing Guide

## Test Credentials
```
Email: admin@demo.com
Password: admin123
URL: https://elev8crm.preview.emergentagent.com
```

---

## Quick Test Commands

### Setup
```bash
# Set your API URL
export API_URL="https://elev8crm.preview.emergentagent.com"

# Get authentication token
export TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

echo "Token: ${TOKEN:0:20}..."
```

---

## Test 1: Lead Management

```bash
# Create a high-scoring lead
curl -X POST "$API_URL/api/elev8/leads" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "Lead",
    "email": "test@example.com",
    "company_name": "Test Corp",
    "sales_motion_type": "partnership_sales",
    "economic_units": 30,
    "usage_volume": 100,
    "urgency": 5,
    "trigger_event": "Budget approved",
    "primary_motivation": "revenue_growth",
    "decision_role": "decision_maker",
    "decision_process_clarity": 5,
    "source": "referral"
  }'

# List leads
curl -s "$API_URL/api/elev8/leads?page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 2: Pipelines

```bash
# Get dual-pipeline configuration
curl -s "$API_URL/api/elev8/pipelines/elev8" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 3: KPI Dashboard

```bash
# Forecasting summary
curl -s "$API_URL/api/elev8/forecasting/summary?period=month" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# KPIs overview
curl -s "$API_URL/api/elev8/kpis/overview?period=month" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Pipeline health
curl -s "$API_URL/api/elev8/ai-assistant/pipeline/health-summary?pipeline_type=sales" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 4: AI Assistant

```bash
# Check AI status
curl -s "$API_URL/api/elev8/ai-assistant/status" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get lead score explanation (replace LEAD_ID)
curl -s "$API_URL/api/elev8/ai-assistant/leads/{LEAD_ID}/score-explanation" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get AI governance rules
curl -s "$API_URL/api/elev8/ai-assistant/governance" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 5: Tasks & SLA

```bash
# Create a task
curl -X POST "$API_URL/api/elev8/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Follow up with prospect",
    "task_type": "call",
    "priority": "high",
    "due_date": "2025-01-15T14:00:00Z"
  }'

# Get SLA status
curl -s "$API_URL/api/elev8/sla/status?entity_type=deals" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get my tasks
curl -s "$API_URL/api/elev8/tasks/my-tasks" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 6: Partner Configuration

```bash
# List partners
curl -s "$API_URL/api/elev8/partners" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get partner config (replace PARTNER_ID)
curl -s "$API_URL/api/elev8/partners/{PARTNER_ID}/config" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get partner KPIs
curl -s "$API_URL/api/elev8/partners/{PARTNER_ID}/kpis?period=month" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Test 7: Handoff to Delivery

```bash
# Get handoff status for a deal (replace DEAL_ID)
curl -s "$API_URL/api/elev8/deals/{DEAL_ID}/handoff-status" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# List all handoffs
curl -s "$API_URL/api/elev8/handoffs" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## UI Testing Checklist

### Leads Page (`/leads`)
- [ ] View lead list with tier badges
- [ ] Create new lead via dialog
- [ ] Click lead row to open detail sheet
- [ ] Click "AI Assistant" button
- [ ] View score breakdown in Intelligence tab
- [ ] Generate outreach draft in Outreach tab

### Pipeline Page (`/pipeline`)
- [ ] Switch between Qualification and Sales tabs
- [ ] View deal cards with tier badges
- [ ] Click deal to open detail sheet
- [ ] Click "AI Assistant - Draft SPICED"
- [ ] View SPICED tab and generate draft
- [ ] Apply draft to form

### KPI Dashboard (`/kpis`)
- [ ] View 4 summary cards
- [ ] Check Forecast tab (tier breakdown)
- [ ] Check Activity KPIs tab
- [ ] Check Pipeline Health tab
- [ ] Check Leaderboard tab
- [ ] Change period selector

### Partners Page (`/partners`)
- [ ] View partner list
- [ ] Create new partner
- [ ] View partner details

### Settings Page (`/settings`)
- [ ] View AI & Intelligence tab
- [ ] Configure AI provider (if needed)

---

## Expected Results Summary

| Feature | Expected Behavior |
|---------|-------------------|
| Lead Creation | Auto-scores and assigns tier |
| Lead Qualification | Creates deal in Sales Pipeline |
| AI Assistant | Shows governance banner, generates drafts |
| KPI Dashboard | Shows pipeline metrics and forecasts |
| SLA Status | Shows compliant/at-risk/breached counts |
| Handoff | Requires Closed Won status, tracks artifacts |

---

## Troubleshooting

**401 Unauthorized**
- Token expired, re-authenticate

**404 Not Found**
- Check entity ID exists
- Ensure correct tenant

**AI Not Configured**
- Add API key in Settings > AI & Intelligence
- Or check EMERGENT_LLM_KEY environment variable

**Score is 0**
- Provide scoring inputs: economic_units, urgency, etc.

---

**Last Updated:** January 2025
