#!/usr/bin/env python3
"""
User-Guardian relationship API test with authentication.
Run: python test_user_guardian_api.py
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_user_guardian_api():
    """Test User-Guardian relationship API endpoints with authentication."""

    print("🔗 Testing User-Guardian Relationship API with Authentication")
    print("=" * 60)

    # Step 1: Create and authenticate a user
    print("\n1. Setting up authenticated user...")
    user_data = {
        "telegram_user_id": 555444333,
        "first_name": "Guardian",
        "last_name": "User",
        "phone_number": "+34666777555",
        "preferred_language": "en",
        "gender": "male",
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
    user = register_response.json()
    user_id = user["id"]
    print("✅ User authenticated successfully")

    # Step 2: Create guardians
    print("\n2. Creating guardians...")
    guardian1_data = {
        "telegram_user_id": 111222333,
        "phone_number": "+34666111222",
        "name": "Guardian One",
        "gender": "female",
    }

    guardian2_data = {
        "telegram_user_id": 444555666,
        "phone_number": "+34666333444",
        "name": "Guardian Two",
        "gender": "male",
    }

    # Create first guardian
    g1_response = client.post(
        "/api/v1/guardians/", json=guardian1_data, headers=headers
    )
    if g1_response.status_code != 201:
        print(f"❌ Guardian 1 creation failed: {g1_response.json()}")
        return False

    guardian1 = g1_response.json()
    guardian1_id = guardian1["id"]
    print(f"✅ Guardian 1 created: {guardian1['name']} ({guardian1_id})")

    # Create second guardian
    g2_response = client.post(
        "/api/v1/guardians/", json=guardian2_data, headers=headers
    )
    if g2_response.status_code != 201:
        print(f"❌ Guardian 2 creation failed: {g2_response.json()}")
        return False

    guardian2 = g2_response.json()
    guardian2_id = guardian2["id"]
    print(f"✅ Guardian 2 created: {guardian2['name']} ({guardian2_id})")

    # Step 3: Link first guardian to user (priority 1)
    print("\n3. Linking first guardian to user...")
    link1_data = {"guardian_id": guardian1_id, "priority_order": 1}

    link1_response = client.post(
        f"/api/v1/users/{user_id}/guardians/", json=link1_data, headers=headers
    )

    if link1_response.status_code != 201:
        print(f"❌ Guardian 1 linking failed: {link1_response.json()}")
        return False

    link1 = link1_response.json()
    print(
        f"✅ Guardian 1 linked: {link1['guardian']['name']} (priority {link1['priority_order']})"
    )

    # Step 4: Link second guardian to user (priority 1 - should push first to priority 2)
    print("\n4. Linking second guardian to user...")
    link2_data = {"guardian_id": guardian2_id, "priority_order": 1}

    link2_response = client.post(
        f"/api/v1/users/{user_id}/guardians/", json=link2_data, headers=headers
    )

    if link2_response.status_code != 201:
        print(f"❌ Guardian 2 linking failed: {link2_response.json()}")
        return False

    link2 = link2_response.json()
    print(
        f"✅ Guardian 2 linked: {link2['guardian']['name']} (priority {link2['priority_order']})"
    )

    # Step 5: List user guardians
    print("\n5. Listing user guardians...")
    list_response = client.get(f"/api/v1/users/{user_id}/guardians/", headers=headers)

    if list_response.status_code != 200:
        print(f"❌ Guardian listing failed: {list_response.json()}")
        return False

    guardian_list = list_response.json()
    print(f"✅ Found {guardian_list['total']} guardian(s):")
    for ug in guardian_list["guardians"]:
        print(f"   - {ug['guardian']['name']} (priority {ug['priority_order']})")

    # Step 6: Update guardian priority
    print("\n6. Updating guardian priority...")
    update_data = {"priority_order": 2}

    update_response = client.put(
        f"/api/v1/users/{user_id}/guardians/{guardian2_id}/priority",
        json=update_data,
        headers=headers,
    )

    if update_response.status_code != 200:
        print(f"❌ Priority update failed: {update_response.json()}")
        return False

    updated_link = update_response.json()
    print(
        f"✅ Priority updated: {updated_link['guardian']['name']} now has priority {updated_link['priority_order']}"
    )

    # Step 7: List guardians again to verify reordering
    print("\n7. Verifying priority reordering...")
    list2_response = client.get(f"/api/v1/users/{user_id}/guardians/", headers=headers)

    if list2_response.status_code != 200:
        print(f"❌ Guardian listing failed: {list2_response.json()}")
        return False

    guardian_list2 = list2_response.json()
    print("✅ Guardian priority order after update:")
    for ug in guardian_list2["guardians"]:
        print(f"   - {ug['guardian']['name']} (priority {ug['priority_order']})")

    # Step 8: Remove a guardian
    print("\n8. Removing a guardian...")
    remove_response = client.delete(
        f"/api/v1/users/{user_id}/guardians/{guardian2_id}", headers=headers
    )

    if remove_response.status_code != 204:
        print(f"❌ Guardian removal failed: status {remove_response.status_code}")
        return False

    print("✅ Guardian removed successfully")

    # Step 9: List guardians to verify removal and reordering
    print("\n9. Verifying guardian removal...")
    list3_response = client.get(f"/api/v1/users/{user_id}/guardians/", headers=headers)

    if list3_response.status_code != 200:
        print(f"❌ Guardian listing failed: {list3_response.json()}")
        return False

    guardian_list3 = list3_response.json()
    print(f"✅ Remaining guardians ({guardian_list3['total']}):")
    for ug in guardian_list3["guardians"]:
        print(f"   - {ug['guardian']['name']} (priority {ug['priority_order']})")

    # Step 10: Test error cases
    print("\n10. Testing error cases...")

    # Try to link non-existent guardian
    fake_link_data = {
        "guardian_id": "00000000-0000-0000-0000-000000000000",
        "priority_order": 1,
    }
    fake_response = client.post(
        f"/api/v1/users/{user_id}/guardians/", json=fake_link_data, headers=headers
    )

    if fake_response.status_code == 201:
        print("❌ Security issue: non-existent guardian link succeeded!")
        return False

    print("✅ Properly rejected non-existent guardian")

    # Test unauthorized access
    unauth_response = client.get(f"/api/v1/users/{user_id}/guardians/")

    if unauth_response.status_code == 200:
        print("❌ Security issue: endpoint accessible without token!")
        return False

    print("✅ Properly blocked unauthorized access")

    return True


if __name__ == "__main__":
    success = test_user_guardian_api()

    print("\n" + "=" * 60)
    if success:
        print("🎉 All User-Guardian relationship API tests passed!")
    else:
        print("❌ Some User-Guardian relationship API tests failed!")
        exit(1)
