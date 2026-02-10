"""Reset demo data (PostgreSQL).

Deletes the demo tenant (slug=demo) and all related data via FK cascades.
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.pg_models.models import Tenant


async def reset_demo(slug: str = "demo") -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = res.scalar_one_or_none()
        if not tenant:
            print(f"No tenant found for slug='{slug}'. Nothing to reset.")
            return

        await session.delete(tenant)
        await session.commit()
        print(f"Deleted tenant slug='{slug}' (id={tenant.id}) and cascaded related data.")


if __name__ == "__main__":
    slug = os.environ.get("DEMO_TENANT_SLUG", "demo")
    asyncio.run(reset_demo(slug))

