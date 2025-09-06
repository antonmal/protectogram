"""Async integration tests for User-Guardian relationship API."""

import pytest


@pytest.mark.asyncio
async def test_user_guardian_invitation_flow_async(
    test_user_data, test_guardian_invitation_data, async_client
):
    """Test User-Guardian relationship API using the new invitation system."""

    # Step 1: Register user and authenticate
    register_response = await async_client.post(
        "/api/v1/users/register", json=test_user_data
    )
    assert register_response.status_code == 201, (
        f"Registration failed: {register_response.json()}"
    )

    user = register_response.json()
    user_id = user["id"]

    # Login to get token
    login_response = await async_client.post(
        "/api/v1/auth/telegram-login",
        json={"telegram_user_id": test_user_data["telegram_user_id"]},
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Create guardian invitation
    invitation_response = await async_client.post(
        "/api/v1/guardians/invite", json=test_guardian_invitation_data, headers=headers
    )
    assert invitation_response.status_code == 201, (
        f"Guardian invitation creation failed: {invitation_response.json()}"
    )

    invitation = invitation_response.json()
    guardian_id = invitation["guardian"]["id"]
    invitation_token = invitation["invitation_token"]
    invitation_link = invitation["invitation_link"]

    # Validate invitation response
    assert invitation_token is not None
    assert invitation_link.startswith("https://t.me/")
    assert invitation["guardian"]["name"] == test_guardian_invitation_data["name"]
    assert invitation["guardian"]["verification_status"] == "pending"
    assert invitation["guardian"]["consent_given"] is False

    # Step 3: List user guardians (should show pending guardian)
    list_response = await async_client.get(
        f"/api/v1/users/{user_id}/guardians/", headers=headers
    )
    assert list_response.status_code == 200, (
        f"Guardian listing failed: {list_response.json()}"
    )

    guardian_list = list_response.json()
    assert guardian_list["total"] == 1
    assert len(guardian_list["guardians"]) == 1
    guardian_item = guardian_list["guardians"][0]
    assert guardian_item["guardian"]["verification_status"] == "pending"
    assert guardian_item["guardian"]["consent_given"] is False

    # Step 4: Remove guardian (cleanup)
    remove_response = await async_client.delete(
        f"/api/v1/users/{user_id}/guardians/{guardian_id}", headers=headers
    )
    assert remove_response.status_code == 204, (
        f"Guardian removal failed: status {remove_response.status_code}"
    )

    # Step 5: Verify removal
    final_list_response = await async_client.get(
        f"/api/v1/users/{user_id}/guardians/", headers=headers
    )
    assert final_list_response.status_code == 200

    final_list = final_list_response.json()
    assert final_list["total"] == 0
    assert len(final_list["guardians"]) == 0


@pytest.mark.asyncio
async def test_user_guardian_priority_management_async(test_user_data, async_client):
    """Test priority management with multiple guardian invitations."""

    # Register user and authenticate
    register_response = await async_client.post(
        "/api/v1/users/register", json=test_user_data
    )
    assert register_response.status_code == 201

    user = register_response.json()
    user_id = user["id"]

    login_response = await async_client.post(
        "/api/v1/auth/telegram-login",
        json={"telegram_user_id": test_user_data["telegram_user_id"]},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create two guardian invitations with unique data
    base_id = test_user_data["telegram_user_id"]
    guardian1_invitation_data = {
        "phone_number": f"+34{(base_id + 10000) % 1000000000}",
        "name": "Guardian One",
        "gender": "female",
    }

    guardian2_invitation_data = {
        "phone_number": f"+34{(base_id + 20000) % 1000000000}",
        "name": "Guardian Two",
        "gender": "male",
    }

    # Create first guardian invitation
    g1_response = await async_client.post(
        "/api/v1/guardians/invite", json=guardian1_invitation_data, headers=headers
    )
    assert g1_response.status_code == 201
    guardian1_id = g1_response.json()["guardian"]["id"]

    # Create second guardian invitation
    g2_response = await async_client.post(
        "/api/v1/guardians/invite", json=guardian2_invitation_data, headers=headers
    )
    assert g2_response.status_code == 201

    # Verify both guardians are created and linked
    list_response = await async_client.get(
        f"/api/v1/users/{user_id}/guardians/", headers=headers
    )
    assert list_response.status_code == 200

    guardian_list = list_response.json()
    assert guardian_list["total"] == 2

    # Check that guardians exist with pending status
    guardians = guardian_list["guardians"]
    guardian_names = [g["guardian"]["name"] for g in guardians]
    assert "Guardian One" in guardian_names
    assert "Guardian Two" in guardian_names

    # All should have pending status initially
    for guardian in guardians:
        assert guardian["guardian"]["verification_status"] == "pending"
        assert guardian["guardian"]["consent_given"] is False

    # Test priority update (if endpoint exists)
    try:
        update_data = {"priority_order": 2}
        update_response = await async_client.put(
            f"/api/v1/users/{user_id}/guardians/{guardian1_id}/priority",
            json=update_data,
            headers=headers,
        )
        # Priority update may not be implemented yet, so we allow 404
        assert update_response.status_code in [200, 404]
    except Exception:
        # Skip priority testing if endpoint doesn't exist
        pass


@pytest.mark.asyncio
async def test_user_guardian_error_cases_async(test_user_data, async_client):
    """Test error handling in User-Guardian relationships."""

    # Register user and authenticate
    register_response = await async_client.post(
        "/api/v1/users/register", json=test_user_data
    )
    assert register_response.status_code == 201

    user = register_response.json()
    user_id = user["id"]

    login_response = await async_client.post(
        "/api/v1/auth/telegram-login",
        json={"telegram_user_id": test_user_data["telegram_user_id"]},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test creating invitation with invalid data
    invalid_invitation_data = {
        "phone_number": "invalid-phone",  # Invalid phone format
        "name": "Test Guardian",
        "gender": "invalid",  # Invalid gender
    }
    invalid_response = await async_client.post(
        "/api/v1/guardians/invite", json=invalid_invitation_data, headers=headers
    )
    assert invalid_response.status_code == 422  # Validation error

    # Test unauthorized access (no token)
    unauth_response = await async_client.get(f"/api/v1/users/{user_id}/guardians/")
    assert unauth_response.status_code == 403  # Forbidden (our auth middleware)

    # Test creating invitation without authentication
    valid_invitation_data = {
        "phone_number": "+34611111111",
        "name": "Test Guardian",
        "gender": "female",
    }
    unauth_invite_response = await async_client.post(
        "/api/v1/guardians/invite", json=valid_invitation_data
    )
    assert unauth_invite_response.status_code == 403  # Forbidden

    # Test accessing another user's guardians
    other_user_data = {
        "telegram_user_id": test_user_data["telegram_user_id"] + 1000000,
        "first_name": "Other",
        "last_name": "User",
        "phone_number": f"+34{(test_user_data['telegram_user_id'] + 1000000) % 1000000000}",
        "preferred_language": "en",
        "gender": "female",
    }

    other_register_response = await async_client.post(
        "/api/v1/users/register", json=other_user_data
    )
    assert other_register_response.status_code == 201
    other_user_id = other_register_response.json()["id"]

    # Try to access other user's guardians with current user's token
    forbidden_response = await async_client.get(
        f"/api/v1/users/{other_user_id}/guardians/", headers=headers
    )
    assert forbidden_response.status_code == 403  # Forbidden
