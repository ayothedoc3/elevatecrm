# CRM OS - Enterprise CRM Platform

A full-stack CRM platform that replaces GoHighLevel for day-to-day operations, combining HubSpot-style CRM data modeling with GHL-style execution speed.

## 🚀 Features

### Core CRM
- **Multi-Tenant Architecture** - Full tenant isolation at database level
- **JWT Authentication** - Secure token-based auth with RBAC (Admin, Manager, Sales Rep, Viewer)
- **Contacts Management** - Full CRUD with search, filters, and lifecycle stages
- **Deals/Opportunities** - Track deals through pipeline stages
- **Timeline Events** - Complete activity history for contacts and deals

### NLA Tax Filing Workflow (15-Step Blueprint)
The system enforces the New Level Accounting tax filing workflow as a first-class, auditable process:

1. Estimate Requested
2. Sign-Up Sent
3. Form Submitted
4. Client Profile Created
5. Questionnaire Sent
6. Questionnaire Completed
7. Docs Received
8. ID Verified
9. Estimate Prepared
10. Estimate Approved
11. Engagement Letter Signed
12. Banking Info Captured
13. Final Docs Signed (1040)
14. Complete + Review Requested
15. Commission Routed

### Workflow Blueprint Framework
- **Stage Requirements** - Required properties and actions per stage
- **Automation Triggers** - Entry/exit automations (SMS, email, document requests)
- **Admin Override** - Override blocked moves with mandatory reason
- **Compliance Tracking** - Compliant / Missing Requirements / Overridden status

### Pipeline & Kanban Board
- Visual Kanban board with all 15 stages
- Drag deals between stages
- Quick actions (Back/Next) for stage movement
- Deal value tracking per stage
- Blueprint compliance badges

### Audit Logging
- Every create/update/delete is logged
- Stage movements tracked
- Actor, action, before/after state captured
- Full traceability for regulated workflows

## 🛠 Tech Stack

- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL + SQLAlchemy
- **Authentication**: JWT tokens
- **ORM**: SQLAlchemy with async support

## 📦 Installation

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Configure backend URL
cp .env.example .env
# Edit REACT_APP_BACKEND_URL if needed

# Run development server
yarn start
```

## 🔐 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.com | admin123 |
| Manager | manager@demo.com | manager123 |
| Sales Rep | sales@demo.com | sales123 |

**Tenant Slug**: `demo`

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register?tenant_slug={slug}` - Register new user
- `POST /api/auth/login?tenant_slug={slug}` - Login
- `GET /api/auth/me` - Get current user

### Contacts
- `GET /api/contacts` - List contacts (paginated, searchable)
- `POST /api/contacts` - Create contact
- `GET /api/contacts/{id}` - Get contact
- `PUT /api/contacts/{id}` - Update contact
- `DELETE /api/contacts/{id}` - Delete contact (Admin/Manager only)

### Deals
- `GET /api/deals` - List deals
- `POST /api/deals` - Create deal
- `GET /api/deals/{id}` - Get deal
- `PUT /api/deals/{id}` - Update deal
- `POST /api/deals/{id}/move-stage` - Move deal to new stage
- `GET /api/deals/{id}/blueprint-progress` - Get blueprint progress

### Pipelines
- `GET /api/pipelines` - List pipelines
- `GET /api/pipelines/{id}` - Get pipeline with stages
- `GET /api/pipelines/{id}/kanban` - Get Kanban board data

### Blueprints
- `GET /api/blueprints` - List blueprints
- `GET /api/blueprints/{id}` - Get blueprint with stages
- `POST /api/blueprints/validate-move` - Validate stage move
- `POST /api/blueprints/override-move` - Admin override move (with reason)

### Timeline
- `GET /api/timeline` - List timeline events
- `POST /api/timeline` - Create timeline event

## 🗄 Database Schema

### Core Tables
- `tenants` - Multi-tenant workspaces
- `users` - User accounts with roles
- `contacts` - CRM contacts
- `companies` - Company records
- `deals` - Opportunities/deals
- `pipelines` - Sales pipelines
- `pipeline_stages` - Pipeline stages
- `workflow_blueprints` - Workflow definitions
- `blueprint_stages` - Blueprint stage requirements
- `timeline_events` - Activity timeline
- `audit_logs` - Full audit trail

## 🔧 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://crm_user:crm_password@localhost:5432/crm_os
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=*
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📋 Roadmap

### Phase 2 (Coming Soon)
- [ ] SMS/Email Integration (Twilio, SendGrid)
- [ ] Automation Engine with triggers/conditions/actions
- [ ] Conversations Inbox
- [ ] Forms & Landing Page Builder

### Phase 3
- [ ] Custom Objects Framework
- [ ] Advanced Reporting Dashboard
- [ ] E-Signature Integration
- [ ] Payment Processing (Stripe)

## 📄 License

Proprietary - All rights reserved.

## 🤝 Support

For support, email support@crm-os.com or join our Slack channel.
