#!/usr/bin/env python3
"""Quick API test for guardian invitations."""

import requests


def test_guardian_invitation_api():
    """Test the guardian invitation API endpoint."""
    base_url = "http://localhost:8000"

    print("🧪 Testing Guardian Invitation API\n")

    # Test data
    guardian_data = {
        "name": "Test Guardian",
        "phone_number": "+1234567890",
        "gender": "other",
    }

    try:
        # Test health first
        print("1️⃣ Testing server health...")
        health = requests.get(f"{base_url}/health")
        if health.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server health check failed: {health.status_code}")
            return

        # Create invitation
        print("2️⃣ Creating guardian invitation...")
        response = requests.post(
            f"{base_url}/api/v1/guardians/invite",
            json=guardian_data,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 201:
            result = response.json()
            print("   ✅ Invitation created successfully!")
            print("   🔗 **Invitation Link:**")
            print(f"      {result['invitation_link']}")
            print(f"   🔑 **Token:** {result['invitation_token'][:20]}...")
            print(f"   ⏰ **Expires:** {result['expires_at']}")
            print(f"   💬 **Message:** {result['message']}")
        else:
            print(f"   ❌ Failed to create invitation: {response.status_code}")
            print(f"   📄 Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running:")
        print("   ./venv/bin/python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_guardian_invitation_api()
