"""Async integration tests for User-Guardian relationship API."""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_user_guardian_relationship_async(test_user_data, test_guardian_data):
    """Test User-Guardian relationship API with proper async handling."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Register user and authenticate
        register_response = await client.post(
            "/api/v1/users/register", json=test_user_data
        )
        assert (
            register_response.status_code == 201
        ), f"Registration failed: {register_response.json()}"

        user = register_response.json()
        user_id = user["id"]

        # Login to get token
        login_response = await client.post(
            "/api/v1/auth/telegram-login",
            json={"telegram_user_id": test_user_data["telegram_user_id"]},
        )
        assert (
            login_response.status_code == 200
        ), f"Login failed: {login_response.json()}"

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create guardian
        guardian_response = await client.post(
            "/api/v1/guardians/", json=test_guardian_data, headers=headers
        )
        assert (
            guardian_response.status_code == 201
        ), f"Guardian creation failed: {guardian_response.json()}"

        guardian = guardian_response.json()
        guardian_id = guardian["id"]

        # Step 3: Link guardian to user
        link_data = {"guardian_id": guardian_id, "priority_order": 1}
        link_response = await client.post(
            f"/api/v1/users/{user_id}/guardians/", json=link_data, headers=headers
        )
        assert (
            link_response.status_code == 201
        ), f"Guardian linking failed: {link_response.json()}"

        link = link_response.json()
        assert link["priority_order"] == 1
        assert link["guardian"]["name"] == test_guardian_data["name"]

        # Step 4: List user guardians
        list_response = await client.get(
            f"/api/v1/users/{user_id}/guardians/", headers=headers
        )
        assert (
            list_response.status_code == 200
        ), f"Guardian listing failed: {list_response.json()}"

        guardian_list = list_response.json()
        assert guardian_list["total"] == 1
        assert len(guardian_list["guardians"]) == 1
        assert guardian_list["guardians"][0]["priority_order"] == 1

        # Step 5: Update guardian priority
        update_data = {"priority_order": 2}
        update_response = await client.put(
            f"/api/v1/users/{user_id}/guardians/{guardian_id}/priority",
            json=update_data,
            headers=headers,
        )
        assert (
            update_response.status_code == 200
        ), f"Priority update failed: {update_response.json()}"

        updated_link = update_response.json()
        assert updated_link["priority_order"] == 2

        # Step 6: Remove guardian
        remove_response = await client.delete(
            f"/api/v1/users/{user_id}/guardians/{guardian_id}", headers=headers
        )
        assert (
            remove_response.status_code == 204
        ), f"Guardian removal failed: status {remove_response.status_code}"

        # Step 7: Verify removal
        final_list_response = await client.get(
            f"/api/v1/users/{user_id}/guardians/", headers=headers
        )
        assert final_list_response.status_code == 200

        final_list = final_list_response.json()
        assert final_list["total"] == 0
        assert len(final_list["guardians"]) == 0


@pytest.mark.asyncio
async def test_user_guardian_priority_management_async(test_user_data):
    """Test priority management with multiple guardians."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user and authenticate
        register_response = await client.post(
            "/api/v1/users/register", json=test_user_data
        )
        assert register_response.status_code == 201

        user = register_response.json()
        user_id = user["id"]

        login_response = await client.post(
            "/api/v1/auth/telegram-login",
            json={"telegram_user_id": test_user_data["telegram_user_id"]},
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create two guardians with unique data
        base_id = test_user_data["telegram_user_id"]
        guardian1_data = {
            "telegram_user_id": base_id + 10000,
            "phone_number": f"+34{(base_id + 10000) % 1000000000}",
            "name": "Guardian One",
            "gender": "female",
        }

        guardian2_data = {
            "telegram_user_id": base_id + 20000,
            "phone_number": f"+34{(base_id + 20000) % 1000000000}",
            "name": "Guardian Two",
            "gender": "male",
        }

        g1_response = await client.post(
            "/api/v1/guardians/", json=guardian1_data, headers=headers
        )
        assert g1_response.status_code == 201
        guardian1_id = g1_response.json()["id"]

        g2_response = await client.post(
            "/api/v1/guardians/", json=guardian2_data, headers=headers
        )
        assert g2_response.status_code == 201
        guardian2_id = g2_response.json()["id"]

        # Link first guardian with priority 1
        link1_response = await client.post(
            f"/api/v1/users/{user_id}/guardians/",
            json={"guardian_id": guardian1_id, "priority_order": 1},
            headers=headers,
        )
        assert link1_response.status_code == 201
        assert link1_response.json()["priority_order"] == 1

        # Link second guardian with priority 1 (should push first to priority 2)
        link2_response = await client.post(
            f"/api/v1/users/{user_id}/guardians/",
            json={"guardian_id": guardian2_id, "priority_order": 1},
            headers=headers,
        )
        assert link2_response.status_code == 201
        assert link2_response.json()["priority_order"] == 1

        # Verify priority ordering
        list_response = await client.get(
            f"/api/v1/users/{user_id}/guardians/", headers=headers
        )
        assert list_response.status_code == 200

        guardian_list = list_response.json()
        assert guardian_list["total"] == 2

        # Check that guardians are ordered by priority
        guardians = guardian_list["guardians"]
        assert guardians[0]["priority_order"] == 1  # Guardian Two (latest)
        assert guardians[0]["guardian"]["name"] == "Guardian Two"
        assert guardians[1]["priority_order"] == 2  # Guardian One (pushed down)
        assert guardians[1]["guardian"]["name"] == "Guardian One"


@pytest.mark.asyncio
async def test_user_guardian_error_cases_async(test_user_data):
    """Test error handling in User-Guardian relationships."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user and authenticate
        register_response = await client.post(
            "/api/v1/users/register", json=test_user_data
        )
        assert register_response.status_code == 201

        user = register_response.json()
        user_id = user["id"]

        login_response = await client.post(
            "/api/v1/auth/telegram-login",
            json={"telegram_user_id": test_user_data["telegram_user_id"]},
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test linking non-existent guardian
        fake_link_data = {
            "guardian_id": "00000000-0000-0000-0000-000000000000",
            "priority_order": 1,
        }
        fake_response = await client.post(
            f"/api/v1/users/{user_id}/guardians/", json=fake_link_data, headers=headers
        )
        assert fake_response.status_code == 400  # Bad request for non-existent guardian

        # Test unauthorized access (no token)
        unauth_response = await client.get(f"/api/v1/users/{user_id}/guardians/")
        assert unauth_response.status_code == 403  # Forbidden (our auth middleware)

        # Test accessing another user's guardians
        other_user_data = {
            "telegram_user_id": test_user_data["telegram_user_id"] + 1000000,
            "first_name": "Other",
            "last_name": "User",
            "phone_number": f"+34{(test_user_data['telegram_user_id'] + 1000000) % 1000000000}",
            "preferred_language": "en",
            "gender": "female",
        }

        other_register_response = await client.post(
            "/api/v1/users/register", json=other_user_data
        )
        assert other_register_response.status_code == 201
        other_user_id = other_register_response.json()["id"]

        # Try to access other user's guardians with current user's token
        forbidden_response = await client.get(
            f"/api/v1/users/{other_user_id}/guardians/", headers=headers
        )
        assert forbidden_response.status_code == 403  # Forbidden
