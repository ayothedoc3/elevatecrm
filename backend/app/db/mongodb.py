"""
MongoDB Database Configuration and Connection
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global database client
_client: Optional[AsyncIOMotorClient] = None
_db = None


def get_database():
    """Get the MongoDB database instance"""
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def init_db():
    """Initialize MongoDB connection"""
    global _client, _db
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "elevate_crm")
    
    logger.info(f"Connecting to MongoDB at {mongo_url}")
    
    _client = AsyncIOMotorClient(mongo_url)
    _db = _client[db_name]
    
    # Create indexes for better query performance
    await create_indexes()
    
    logger.info(f"Connected to MongoDB database: {db_name}")
    return _db


async def close_db():
    """Close MongoDB connection"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


async def create_indexes():
    """Create database indexes for better performance"""
    db = get_database()
    
    # Users indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("tenant_id")
    
    # Tenants indexes
    await db.tenants.create_index("slug", unique=True)
    
    # Contacts indexes
    await db.contacts.create_index("tenant_id")
    await db.contacts.create_index("email")
    await db.contacts.create_index([("tenant_id", 1), ("email", 1)])
    
    # Deals indexes
    await db.deals.create_index("tenant_id")
    await db.deals.create_index("pipeline_id")
    await db.deals.create_index("stage_id")
    await db.deals.create_index("contact_id")
    await db.deals.create_index([("tenant_id", 1), ("status", 1)])
    
    # Pipelines indexes
    await db.pipelines.create_index("tenant_id")
    await db.pipeline_stages.create_index("pipeline_id")
    
    # Timeline events indexes
    await db.timeline_events.create_index("tenant_id")
    await db.timeline_events.create_index([("tenant_id", 1), ("created_at", -1)])
    await db.timeline_events.create_index("deal_id")
    await db.timeline_events.create_index("contact_id")
    
    # Outreach activities indexes
    await db.outreach_activities.create_index("tenant_id")
    await db.outreach_activities.create_index("deal_id")
    
    # Custom objects indexes
    await db.custom_object_definitions.create_index("tenant_id")
    await db.custom_object_definitions.create_index([("tenant_id", 1), ("slug", 1)], unique=True)
    await db.custom_object_records.create_index("object_id")
    await db.custom_object_records.create_index("tenant_id")
    
    # Calculation definitions indexes
    await db.calculation_definitions.create_index("tenant_id")
    await db.calculation_results.create_index("deal_id")
    
    # Blueprints indexes
    await db.crm_blueprints.create_index("slug", unique=True)
    await db.workspaces.create_index("tenant_id")
    
    # Settings module indexes
    await db.workspace_settings.create_index("workspace_id", unique=True)
    await db.workspace_integrations.create_index([("workspace_id", 1), ("provider_type", 1)], unique=True)
    await db.workspace_integrations.create_index("workspace_id")
    await db.ai_usage_configs.create_index("workspace_id", unique=True)
    await db.ai_usage_logs.create_index([("workspace_id", 1), ("timestamp", -1)])
    await db.ai_usage_logs.create_index([("workspace_id", 1), ("feature_type", 1)])
    await db.settings_audit_logs.create_index([("workspace_id", 1), ("timestamp", -1)])
    await db.settings_audit_logs.create_index([("workspace_id", 1), ("action", 1)])
    await db.affiliate_settings.create_index("workspace_id", unique=True)
    
    logger.info("Database indexes created")


# Helper function to convert ObjectId to string in documents
def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == "_id":
                continue  # Skip _id, we use our own 'id' field
            result[key] = serialize_doc(value)
        return result
    return doc
