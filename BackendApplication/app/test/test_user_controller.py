import sys
import os
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime

# Add the project root to the Python path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from ...main import app
from ..model.user import User

client = TestClient(app)


def test_print_routes():
    """Diagnostic test to print all registered routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods) if hasattr(route, "methods") else []
            })
    print("\n--- REGISTERED ROUTES ---")
    print(json.dumps(routes, indent=2))
    print("--- END REGISTERED ROUTES ---")
    assert False, "Stopping test to print routes for analysis."


@pytest.fixture
def mock_user_service():
    """Fixture to patch the user service with an async mock."""
    with patch('app.controller.user_controller.service', new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_register_user(mock_user_service):
    """Test user registration endpoint."""
    mock_user_service.register_user.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )

    response = client.post(
        "/api/v1/users/register",
        json={"gmail": "test@example.com", "username": "testuser", "password": "password"}
    )

    assert response.status_code == 201, response.text
    json_response = response.json()
    assert json_response["gmail"] == "test@example.com"
    assert "id" in json_response
    mock_user_service.register_user.assert_awaited_once_with(
        gmail="test@example.com",
        username="testuser",
        password="password"
    )


@pytest.mark.asyncio
async def test_login_user(mock_user_service):
    """Test user login endpoint."""
    mock_user_service.authenticate_user.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )

    response = client.post(
        "/api/v1/users/login",
        json={"gmail": "test@example.com", "password": "password"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["gmail"] == "test@example.com"
    mock_user_service.authenticate_user.assert_awaited_once_with(
        gmail="test@example.com",
        password="password"
    )


@pytest.mark.asyncio
async def test_get_user(mock_user_service):
    """Test get user by ID endpoint."""
    mock_user_service.get_user_by_id.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )

    response = client.get("/api/v1/users/1")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == 1
    mock_user_service.get_user_by_id.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_update_user(mock_user_service):
    """Test update user profile endpoint."""
    mock_user_service.update_user_profile.return_value = User(
        id=1,
        gmail="test@example.com",
        username="newusername",
        created_at=datetime.now()
    )

    response = client.put(
        "/api/v1/users/1",
        json={"username": "newusername"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["username"] == "newusername"
    mock_user_service.update_user_profile.assert_awaited_once_with(1, username='newusername')


@pytest.mark.asyncio
async def test_change_password(mock_user_service):
    """Test change user password endpoint."""
    mock_user_service.change_password.return_value = True

    response = client.post(
        "/api/v1/users/1/change-password",
        json={"old_password": "oldpassword", "new_password": "newpassword"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Password changed successfully"
    mock_user_service.change_password.assert_awaited_once_with(
        user_id=1,
        old_password="oldpassword",
        new_password="newpassword"
    )


@pytest.mark.asyncio
async def test_delete_user(mock_user_service):
    """Test delete user endpoint."""
    mock_user_service.delete_user.return_value = True

    response = client.delete("/api/v1/users/1")

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "User deleted successfully"
    mock_user_service.delete_user.assert_awaited_once_with(1)
