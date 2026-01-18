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

    print(f"Deleted {result1.deleted_count} tenants")
    print(f"Deleted {result2.deleted_count} users")
    print(f"Deleted {result3.deleted_count} contacts")
    print(f"Deleted {result4.deleted_count} deals")
    print(f"Deleted {result5.deleted_count} pipelines")
    print(f"Deleted {result6.deleted_count} pipeline stages")
    print("Demo data reset complete!")

    client.close()

if __name__ == "__main__":
    asyncio.run(reset_demo())
