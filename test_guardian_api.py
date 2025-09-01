#!/usr/bin/env python3
"""
Guardian API test with authentication.
Run: python test_guardian_api.py
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_guardian_api():
    """Test Guardian API endpoints with authentication."""

    print("🛡️ Testing Guardian API with Authentication")
    print("=" * 60)

    # Step 1: Create and authenticate a user
    print("\n1. Setting up authenticated user...")
    user_data = {
        "telegram_user_id": 999888777,
        "first_name": "Guardian",
        "last_name": "Test",
        "preferred_language": "en",
        "gender": "female",
    }

    # Register user
    register_response = client.post("/api/v1/users/register", json=user_data)
    if register_response.status_code != 201:
        print(f"❌ User registration failed: {register_response.json()}")
        return False

    # Login to get token
    login_response = client.post(
        "/api/v1/auth/telegram-login",
        json={"telegram_user_id": user_data["telegram_user_id"]},
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.json()}")
        return False

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ User authenticated successfully")

    # Step 2: Create a guardian
    print("\n2. Creating guardian...")
    guardian_data = {
        "telegram_user_id": 123987654,
        "phone_number": "+34666123456",
        "name": "María García",
        "gender": "female",
    }

    create_response = client.post(
        "/api/v1/guardians/", json=guardian_data, headers=headers
    )

    print(f"Guardian creation status: {create_response.status_code}")
    if create_response.status_code != 201:
        print(f"❌ Guardian creation failed: {create_response.json()}")
        return False

    guardian = create_response.json()
    guardian_id = guardian["id"]
    print(f"✅ Guardian created: {guardian['name']} ({guardian_id})")

    # Step 3: Get guardian by ID
    print("\n3. Retrieving guardian by ID...")
    get_response = client.get(f"/api/v1/guardians/{guardian_id}", headers=headers)

    if get_response.status_code != 200:
        print(f"❌ Guardian retrieval failed: {get_response.json()}")
        return False

    retrieved_guardian = get_response.json()
    print(f"✅ Guardian retrieved: {retrieved_guardian['name']}")

    # Step 4: Get guardian by phone number
    print("\n4. Retrieving guardian by phone number...")
    phone_response = client.get(
        f"/api/v1/guardians/phone/{guardian_data['phone_number']}", headers=headers
    )

    if phone_response.status_code != 200:
        print(f"❌ Guardian phone lookup failed: {phone_response.json()}")
        return False

    phone_guardian = phone_response.json()
    print(f"✅ Guardian found by phone: {phone_guardian['name']}")

    # Step 5: Update guardian
    print("\n5. Updating guardian...")
    update_data = {"name": "María García López"}

    update_response = client.put(
        f"/api/v1/guardians/{guardian_id}", json=update_data, headers=headers
    )

    if update_response.status_code != 200:
        print(f"❌ Guardian update failed: {update_response.json()}")
        return False

    updated_guardian = update_response.json()
    print(f"✅ Guardian updated: {updated_guardian['name']}")

    # Step 6: List guardians
    print("\n6. Listing guardians...")
    list_response = client.get("/api/v1/guardians/", headers=headers)

    if list_response.status_code != 200:
        print(f"❌ Guardian listing failed: {list_response.json()}")
        return False

    guardian_list = list_response.json()
    print(f"✅ Found {guardian_list['total']} guardian(s)")

    # Step 7: Search guardians
    print("\n7. Searching guardians...")
    search_response = client.get("/api/v1/guardians/?search=María", headers=headers)

    if search_response.status_code != 200:
        print(f"❌ Guardian search failed: {search_response.json()}")
        return False

    search_results = search_response.json()
    print(f"✅ Search found {len(search_results['guardians'])} guardian(s)")

    # Step 8: Test unauthorized access
    print("\n8. Testing unauthorized access...")
    unauth_response = client.get("/api/v1/guardians/")

    if unauth_response.status_code == 200:
        print("❌ Security issue: endpoint accessible without token!")
        return False

    print("✅ Properly blocked unauthorized access")

    return True


if __name__ == "__main__":
    success = test_guardian_api()

    print("\n" + "=" * 60)
    if success:
        print("🎉 All Guardian API tests passed!")
    else:
        print("❌ Some Guardian API tests failed!")
        exit(1)
