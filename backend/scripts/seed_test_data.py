"""
Seed Data Script for Tasks, SLA Breaches, and Handoff Testing

Run this script to populate the database with realistic test data
for Tasks & SLA, Handoff, and Partner Config features.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'crm_db')


async def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


async def seed_tasks(db, tenant_id: str, user_id: str):
    """Create sample tasks with various states"""
    now = datetime.now(timezone.utc)
    
    # Get some deals and leads to link tasks to
    deals = await db.deals.find({"tenant_id": tenant_id}, {"id": 1, "name": 1}).to_list(5)
    leads = await db.leads.find({"tenant_id": tenant_id}, {"id": 1, "first_name": 1, "last_name": 1}).to_list(5)
    
    tasks = [
        # Overdue tasks
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Follow up with Acme Corp decision maker",
            "description": "Call to discuss pricing proposal and next steps",
            "task_type": "call",
            "priority": "high",
            "due_date": (now - timedelta(days=3)).isoformat(),
            "deal_id": deals[0]["id"] if deals else None,
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": (now - timedelta(days=5)).isoformat(),
            "updated_at": (now - timedelta(days=5)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Send proposal revision",
            "description": "Update pricing based on customer feedback",
            "task_type": "proposal",
            "priority": "urgent",
            "due_date": (now - timedelta(days=1)).isoformat(),
            "deal_id": deals[1]["id"] if len(deals) > 1 else None,
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": (now - timedelta(days=4)).isoformat(),
            "updated_at": (now - timedelta(days=4)).isoformat()
        },
        # Due today
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Demo scheduled with TechStart Inc",
            "description": "Product demonstration for new prospect",
            "task_type": "demo",
            "priority": "high",
            "due_date": now.isoformat(),
            "lead_id": leads[0]["id"] if leads else None,
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Contract review meeting",
            "description": "Legal review of enterprise contract",
            "task_type": "meeting",
            "priority": "medium",
            "due_date": now.isoformat(),
            "deal_id": deals[2]["id"] if len(deals) > 2 else None,
            "assigned_to": user_id,
            "status": "in_progress",
            "created_by": user_id,
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": now.isoformat()
        },
        # Upcoming tasks
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "First touch email to new referral",
            "description": "Personalized outreach to warm referral lead",
            "task_type": "email",
            "priority": "medium",
            "due_date": (now + timedelta(days=1)).isoformat(),
            "lead_id": leads[1]["id"] if len(leads) > 1 else None,
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Discovery call with Global Foods",
            "description": "Initial discovery to understand requirements",
            "task_type": "call",
            "priority": "high",
            "due_date": (now + timedelta(days=2)).isoformat(),
            "deal_id": deals[3]["id"] if len(deals) > 3 else None,
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Prepare quarterly pipeline review",
            "description": "Compile data for management review",
            "task_type": "review",
            "priority": "low",
            "due_date": (now + timedelta(days=5)).isoformat(),
            "assigned_to": user_id,
            "status": "pending",
            "created_by": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        # Completed task
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "title": "Send case study to prospect",
            "description": "Share relevant success story",
            "task_type": "email",
            "priority": "medium",
            "due_date": (now - timedelta(days=2)).isoformat(),
            "lead_id": leads[2]["id"] if len(leads) > 2 else None,
            "assigned_to": user_id,
            "status": "completed",
            "completed_at": (now - timedelta(days=2)).isoformat(),
            "completed_by": user_id,
            "created_by": user_id,
            "created_at": (now - timedelta(days=4)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat()
        }
    ]
    
    # Insert tasks
    for task in tasks:
        await db.tasks.update_one(
            {"id": task["id"]},
            {"$set": task},
            upsert=True
        )
    
    print(f"✅ Created {len(tasks)} sample tasks")
    return tasks


async def seed_sla_configs(db, tenant_id: str, user_id: str):
    """Create SLA configurations"""
    now = datetime.now(timezone.utc)
    
    sla_configs = [
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": "Standard Lead Response",
            "stage": None,
            "source": None,
            "max_hours": 24,
            "escalation_hours": 12,
            "applies_to": "leads",
            "is_default": False,
            "created_at": now.isoformat(),
            "created_by": user_id
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": "Referral Priority Response",
            "stage": None,
            "source": "referral",
            "max_hours": 4,
            "escalation_hours": 2,
            "applies_to": "leads",
            "is_default": False,
            "created_at": now.isoformat(),
            "created_by": user_id
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": "Deal Activity SLA",
            "stage": None,
            "source": None,
            "max_hours": 72,
            "escalation_hours": 48,
            "applies_to": "deals",
            "is_default": False,
            "created_at": now.isoformat(),
            "created_by": user_id
        },
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "name": "Demo Stage Activity",
            "stage": "Discovery / Demo Scheduled",
            "source": None,
            "max_hours": 48,
            "escalation_hours": 24,
            "applies_to": "deals",
            "is_default": False,
            "created_at": now.isoformat(),
            "created_by": user_id
        }
    ]
    
    for config in sla_configs:
        await db.sla_configs.update_one(
            {"id": config["id"]},
            {"$set": config},
            upsert=True
        )
    
    print(f"✅ Created {len(sla_configs)} SLA configurations")
    return sla_configs


async def create_sla_breach_scenarios(db, tenant_id: str):
    """Update some leads/deals to simulate SLA breaches"""
    now = datetime.now(timezone.utc)
    
    # Update a few leads to be stale (simulate SLA breaches)
    stale_time = (now - timedelta(hours=96)).isoformat()  # 4 days old
    at_risk_time = (now - timedelta(hours=60)).isoformat()  # 2.5 days old
    
    # Update 2 leads to be breached
    result = await db.leads.update_many(
        {"tenant_id": tenant_id, "status": {"$in": ["new", "working"]}},
        {"$set": {"updated_at": stale_time}},
        limit=2
    )
    
    # Update 2 deals to be at risk
    await db.deals.update_many(
        {"tenant_id": tenant_id, "status": "open"},
        {"$set": {"updated_at": at_risk_time}},
        limit=2
    )
    
    print(f"✅ Created SLA breach/at-risk scenarios")


async def seed_won_deals_for_handoff(db, tenant_id: str, user_id: str):
    """Create or update deals to 'won' status for handoff testing"""
    now = datetime.now(timezone.utc)
    
    # Check existing won deals
    won_count = await db.deals.count_documents({"tenant_id": tenant_id, "status": "won"})
    
    if won_count < 3:
        # Get some open deals and mark them as won
        open_deals = await db.deals.find(
            {"tenant_id": tenant_id, "status": "open"},
            {"id": 1}
        ).limit(3 - won_count).to_list(3 - won_count)
        
        for deal in open_deals:
            await db.deals.update_one(
                {"id": deal["id"]},
                {"$set": {
                    "status": "won",
                    "stage_name": "Closed Won",
                    "spiced_situation": "Customer needed to modernize their operations",
                    "spiced_pain": "Manual processes causing delays and errors",
                    "spiced_impact": "30% efficiency improvement expected",
                    "spiced_critical_event": "Budget approval in Q1",
                    "spiced_economic": "ROI positive within 6 months",
                    "spiced_decision": "CTO is final decision maker",
                    "updated_at": now.isoformat()
                }}
            )
        
        print(f"✅ Marked {len(open_deals)} deals as won for handoff testing")
    else:
        print(f"✅ Already have {won_count} won deals for handoff testing")


async def seed_partner_configs(db, tenant_id: str, user_id: str):
    """Create sample partner configurations"""
    now = datetime.now(timezone.utc)
    
    # Get partners
    partners = await db.partners.find({"tenant_id": tenant_id}, {"id": 1, "name": 1}).to_list(5)
    
    if not partners:
        print("⚠️ No partners found. Skipping partner config seeding.")
        return
    
    for partner in partners:
        config = {
            "id": str(uuid.uuid4()),
            "partner_id": partner["id"],
            "tenant_id": tenant_id,
            "pipeline_config": {
                "stage_mappings": {},
                "skip_stages": [],
                "custom_stages": []
            },
            "field_config": {
                "required_at_qualification": ["economic_units", "urgency"],
                "required_at_discovery": ["spiced_situation", "spiced_pain"],
                "required_at_proposal": ["amount"],
                "required_at_close": ["spiced_summary"],
                "custom_fields": []
            },
            "kpi_config": {
                "target_win_rate": 25.0 + (hash(partner["id"]) % 15),  # Vary targets
                "target_deal_size": 5000 + (hash(partner["id"]) % 10000),
                "target_cycle_days": 30 + (hash(partner["id"]) % 30),
                "target_qualification_rate": 25.0 + (hash(partner["id"]) % 20),
                "custom_kpis": []
            },
            "compliance_config": {
                "rules": [
                    "All deals over $50,000 require manager approval",
                    "Contract terms must be reviewed by legal"
                ],
                "required_certifications": [],
                "approval_thresholds": {
                    "contract_value": 50000,
                    "discount": 15
                },
                "mandatory_reviews": []
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "updated_by": user_id
        }
        
        await db.partner_configs.update_one(
            {"partner_id": partner["id"]},
            {"$set": config},
            upsert=True
        )
    
    print(f"✅ Created/updated configs for {len(partners)} partners")


async def main():
    print("\n🌱 Seeding Test Data for Elevate CRM...\n")
    
    db = await get_db()
    
    # Get default tenant and admin user
    user = await db.users.find_one({"email": "admin@demo.com"})
    if not user:
        print("❌ Admin user not found. Please ensure the app has been initialized.")
        return
    
    tenant_id = user.get("tenant_id")
    user_id = user.get("id")
    
    print(f"Using tenant: {tenant_id}")
    print(f"Using user: {user_id}\n")
    
    # Seed data
    await seed_tasks(db, tenant_id, user_id)
    await seed_sla_configs(db, tenant_id, user_id)
    await create_sla_breach_scenarios(db, tenant_id)
    await seed_won_deals_for_handoff(db, tenant_id, user_id)
    await seed_partner_configs(db, tenant_id, user_id)
    
    print("\n✅ Seed data creation complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
