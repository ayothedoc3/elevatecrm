"""Reset demo data"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def reset_demo():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["elevate_crm"]

    # Delete demo tenant and related data
    result1 = await db.tenants.delete_many({"slug": "demo"})
    result2 = await db.users.delete_many({})
    result3 = await db.contacts.delete_many({})
    result4 = await db.deals.delete_many({})
    result5 = await db.pipelines.delete_many({})
    result6 = await db.pipeline_stages.delete_many({})
    result7 = await db.partners.delete_many({})
    result8 = await db.products.delete_many({})
    result9 = await db.accounts.delete_many({})
    result10 = await db.tasks.delete_many({})
    result11 = await db.deal_handoffs.delete_many({})
    result12 = await db.outreach_activities.delete_many({})
    result13 = await db.timeline_events.delete_many({})
    result14 = await db.calculation_definitions.delete_many({})
    result15 = await db.calculation_results.delete_many({})

    print(f"Deleted {result1.deleted_count} tenants")
    print(f"Deleted {result2.deleted_count} users")
    print(f"Deleted {result3.deleted_count} contacts")
    print(f"Deleted {result4.deleted_count} deals")
    print(f"Deleted {result5.deleted_count} pipelines")
    print(f"Deleted {result6.deleted_count} pipeline stages")
    print(f"Deleted {result7.deleted_count} partners")
    print(f"Deleted {result8.deleted_count} products")
    print(f"Deleted {result9.deleted_count} accounts")
    print(f"Deleted {result10.deleted_count} tasks")
    print(f"Deleted {result11.deleted_count} deal handoffs")
    print(f"Deleted {result12.deleted_count} outreach activities")
    print(f"Deleted {result13.deleted_count} timeline events")
    print(f"Deleted {result14.deleted_count} calculation definitions")
    print(f"Deleted {result15.deleted_count} calculation results")
    print("Demo data reset complete!")

    client.close()

if __name__ == "__main__":
    asyncio.run(reset_demo())
