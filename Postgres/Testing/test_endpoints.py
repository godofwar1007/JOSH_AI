# test_endpoints.py
import httpx
import asyncio
import time

BASE_URL = "http://localhost:8000"

async def test_endpoints():
    unique_email = f"test_{int(time.time())}@example.com"
    
    user_data = {
        "name": "Endpoint User",
        "email": unique_email,
        "adv_rank": 5000,
        "mains_rank": 20000,
        "category": "OPEN",
        "gender": "Male",          
        "preferred_branches": ["CS", "IT"],
        "usage": {"queries_today": 0, "cooldown_until": None, "last_query": None}
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/users", json=user_data)
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        user = resp.json()
        user_id = user["id"]
        print(f"✅ Created user: id={user_id}, email={user['email']}")
        
        resp = await client.get(f"{BASE_URL}/users/{user_id}")
        assert resp.status_code == 200
        fetched = resp.json()
        print(f"✅ Fetched user: name={fetched['name']}")
        
        patch_data = {"name": "Patched Name", "adv_rank": 6000}
        resp = await client.patch(f"{BASE_URL}/users/{user_id}", json=patch_data)
        assert resp.status_code == 200
        patched = resp.json()
        print(f"✅ Patched: name={patched['name']}, adv_rank={patched['adv_rank']}")
        
        resp = await client.delete(f"{BASE_URL}/users/{user_id}")
        assert resp.status_code == 200
        print(f"✅ Deleted user")
        
        resp = await client.get(f"{BASE_URL}/users/{user_id}")
        assert resp.status_code == 404
        print("✅ 404 as expected after deletion")
        
        print("\nAll endpoint tests passed!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
