# test_db_functions.py
import asyncio
import time
from user_crud import (
    engine, Base, LocalSession,
    create_user, get_by_email, get_by_id, update_user, delete_user,
    create_schema, upadate_schema, usage_schema,
    Gender, Category
)

async def setup_db():
    """Create tables if they don't exist (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def test_crud():
    await setup_db()
    
    # Generate a unique email based on timestamp
    unique_email = f"test_{int(time.time())}@example.com"
    
    async with LocalSession() as db:
        # 1. Create a user
        user_in = create_schema(
            name="Test User",
            email=unique_email,
            adv_rank=1000,
            mains_rank=500,
            category=Category.OBC_NCL,
            gender=Gender.male,
            preferred_branches=["CS", "EE"],
            usage=usage_schema(queries_today=5)
        )
        new_user = await create_user(db, user_in)
        print(f"✅ Created user: id={new_user.id}, name={new_user.name}, email={new_user.email}")

        # 2. Get by email (using the unique email)
        fetched = await get_by_email(db, unique_email)
        print(f"✅ Get by email: {fetched.name if fetched else 'Not found'}")

        # 3. Get by id
        by_id = await get_by_id(db, new_user.id)
        if by_id is None:
            print("❌ get_by_id returned None")
        else:
            print(f"✅ Get by id: {by_id.name}")

        # 4. Update user – using upadate_schema
        update_data = upadate_schema(name="Updated Name", adv_rank=2000)
        updated = await update_user(db, new_user.id, update_data)
        if updated:
            print(f"✅ Updated: name={updated.name}, adv_rank={updated.adv_rank}")
        else:
            print("❌ Update failed – user not found")

        # 5. Delete user
        deleted = await delete_user(db, new_user.id)
        print(f"✅ Deleted: {deleted}")

        # 6. Verify deletion
        gone = await get_by_id(db, new_user.id)
        print(f"✅ After delete: {gone} (should be None)")

if __name__ == "__main__":
    asyncio.run(test_crud())
