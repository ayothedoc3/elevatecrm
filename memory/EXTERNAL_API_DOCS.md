# Elevate CRM External API Documentation

## Overview

The External API allows Labyrinth OS (or any external system) to integrate with Elevate CRM via:
- **Pull API**: Fetch bulk data on demand
- **Push API**: Receive real-time webhooks when events occur

## Authentication

All External API requests require an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: elk_your_api_key_here" \
  https://your-crm-url/api/external/deals
```

## API Key Management

### Create API Key
```bash
POST /api/external/api-keys?tenant_id={tenant_id}
Content-Type: application/json

{
  "name": "Labyrinth OS Integration",
  "permissions": ["read", "write", "webhook"],
  "expires_in_days": null  // null = never expires
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Labyrinth OS Integration",
  "key": "elk_abc123...",  // SAVE THIS - only shown once!
  "permissions": ["read", "write", "webhook"],
  "created_at": "2026-01-10T00:00:00Z",
  "expires_at": null
}
```

### List API Keys
```bash
GET /api/external/api-keys?tenant_id={tenant_id}
```

### Revoke API Key
```bash
DELETE /api/external/api-keys/{key_id}?tenant_id={tenant_id}
```

---

## Pull API Endpoints

### Get Deals
```bash
GET /api/external/deals
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter: open, won, lost |
| stage | string | Filter by stage name |
| since | ISO timestamp | Get deals updated since this time |
| page | int | Page number (default: 1) |
| page_size | int | Items per page (1-500, default: 50) |

**Response:**
```json
{
  "deals": [...],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "has_more": true
}
```

### Get Leads
```bash
GET /api/external/leads
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status |
| tier | string | Filter: A, B, C, D |
| since | ISO timestamp | Get leads updated since this time |
| page | int | Page number |
| page_size | int | Items per page |

### Get Tasks
```bash
GET /api/external/tasks
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter: pending, completed, overdue |
| priority | string | Filter: low, medium, high, urgent |
| since | ISO timestamp | Get tasks updated since this time |

### Get KPIs
```bash
GET /api/external/kpis?period=month
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| period | string | week, month, quarter, year |

**Response:**
```json
{
  "period": "month",
  "period_start": "2026-01-01T00:00:00Z",
  "generated_at": "2026-01-10T00:00:00Z",
  "leads": {
    "total": 100,
    "qualified": 25,
    "qualification_rate": 25.0
  },
  "deals": {
    "total": 50,
    "open": 30,
    "won": 15,
    "lost": 5,
    "win_rate": 75.0
  },
  "pipeline": {
    "value": 500000,
    "won_value": 250000
  },
  "tasks": {
    "total": 200,
    "overdue": 10
  }
}
```

### Get Pipeline Data
```bash
GET /api/external/pipeline
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| pipeline_type | string | Filter: qualification, sales |

### Get Activity Log
```bash
GET /api/external/activity
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| entity_type | string | Filter: deal, lead, task |
| entity_id | string | Filter by specific entity |
| since | ISO timestamp | Get activity since this time |

### Get Partners
```bash
GET /api/external/partners
```

---

## Push API (Webhooks)

### Register Webhook
```bash
POST /api/external/webhooks
Content-Type: application/json
X-API-Key: elk_your_key

{
  "url": "https://labyrinth-os.example.com/webhooks/crm",
  "events": ["deal.stage_changed", "deal.won", "lead.created"],
  "is_active": true,
  "headers": {
    "X-Custom-Header": "value"
  }
}
```

**Available Events:**
| Event | Description |
|-------|-------------|
| `deal.created` | New deal created |
| `deal.updated` | Deal details updated |
| `deal.stage_changed` | Deal moved to different stage |
| `deal.won` | Deal marked as won |
| `deal.lost` | Deal marked as lost |
| `lead.created` | New lead created |
| `lead.updated` | Lead details updated |
| `lead.qualified` | Lead qualified |
| `lead.disqualified` | Lead disqualified |
| `task.created` | New task created |
| `task.completed` | Task marked complete |
| `task.overdue` | Task became overdue |
| `sla.breach` | SLA breached |
| `sla.warning` | SLA breach approaching |
| `handoff.initiated` | Deal handoff started |
| `handoff.completed` | Deal handoff completed |
| `*` | All events (wildcard) |

### Webhook Payload
```json
{
  "event_type": "deal.stage_changed",
  "timestamp": "2026-01-10T10:00:00Z",
  "tenant_id": "uuid",
  "data": {
    // Full entity data
  },
  "metadata": {
    "old_stage": "Discovery",
    "new_stage": "Proposal"
  }
}
```

### Webhook Headers
Each webhook request includes:
- `Content-Type: application/json`
- `X-Webhook-Signature: sha256={signature}`
- `X-Webhook-Event: {event_type}`
- `X-Webhook-Timestamp: {ISO timestamp}`

### Verifying Webhook Signatures
```python
import hmac
import hashlib

def verify_signature(payload_body, signature_header, secret):
    expected = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    received = signature_header.replace('sha256=', '')
    return hmac.compare_digest(expected, received)
```

### List Webhooks
```bash
GET /api/external/webhooks
X-API-Key: elk_your_key
```

### Update Webhook
```bash
PUT /api/external/webhooks/{webhook_id}
X-API-Key: elk_your_key
Content-Type: application/json

{
  "url": "https://new-url.com/webhook",
  "events": ["*"],
  "is_active": true
}
```

### Delete Webhook
```bash
DELETE /api/external/webhooks/{webhook_id}
X-API-Key: elk_your_key
```

### Test Webhook
```bash
POST /api/external/webhooks/test/{webhook_id}
X-API-Key: elk_your_key
```

---

## Rate Limits

- **Pull API**: 100 requests per minute
- **Webhooks**: Up to 1000 deliveries per hour

## Error Responses

```json
{
  "detail": "Error message"
}
```

| Status Code | Description |
|-------------|-------------|
| 401 | Invalid or missing API key |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Quick Start for Labyrinth OS

1. **Create API Key** (one-time setup via CRM Settings or API)
2. **Store the key securely** in Labyrinth OS config
3. **Register webhooks** for real-time events you care about
4. **Implement webhook handler** with signature verification
5. **Poll Pull APIs** for bulk data sync as needed

Example Labyrinth OS integration:
```python
import httpx

CRM_URL = "https://your-crm.com/api/external"
API_KEY = "elk_your_key"

headers = {"X-API-Key": API_KEY}

# Get all open deals
deals = httpx.get(f"{CRM_URL}/deals?status=open", headers=headers).json()

# Get KPIs for dashboard
kpis = httpx.get(f"{CRM_URL}/kpis?period=week", headers=headers).json()
```
