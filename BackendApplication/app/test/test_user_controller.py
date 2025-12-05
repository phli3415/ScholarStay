
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from main import app  # Assuming your FastAPI app is in main.py
from ..model.user import User
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_user_service():
    with patch('..service.user_service.UserService') as mock:
        yield mock

def test_register_user(mock_user_service):
    mock_user_service.register_user.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )
    response = client.post(
        "/register",
        json={"gmail": "test@example.com", "username": "testuser", "password": "password"}
    )
    assert response.status_code == 201
    assert response.json()["gmail"] == "test@example.com"

def test_login_user(mock_user_service):
    mock_user_service.authenticate_user.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )
    response = client.post(
        "/login",
        json={"gmail": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200
    assert response.json()["gmail"] == "test@example.com"

def test_get_user(mock_user_service):
    mock_user_service.get_user_by_id.return_value = User(
        id=1,
        gmail="test@example.com",
        username="testuser",
        created_at=datetime.now()
    )
    response = client.get("/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_update_user(mock_user_service):
    mock_user_service.update_user_profile.return_value = User(
        id=1,
        gmail="test@example.com",
        username="newusername",
        created_at=datetime.now()
    )
    response = client.put(
        "/1",
        json={"username": "newusername"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "newusername"

def test_change_password(mock_user_service):
    mock_user_service.change_password.return_value = True
    response = client.post(
        "/1/change-password",
        json={"old_password": "oldpassword", "new_password": "newpassword"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

def test_delete_user(mock_user_service):
    mock_user_service.delete_user.return_value = True
    response = client.delete("/1")
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"
