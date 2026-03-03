import pytest

from src.main import app
from src.services.auth_service import AuthService
from src.api.v1.auth import get_auth_service


@pytest.fixture
async def auth_client(client, db_session):
    """HTTP client with the auth service dependency overridden."""
    async def override():
        try:
            yield AuthService(db_session)
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_auth_service] = override
    yield client


class TestRegister:
    async def test_success(self, auth_client):
        response = await auth_client.post("/auth/register", json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        })
        assert response.status_code == 201
        body = response.json()
        assert body["username"] == "alice"
        assert body["email"] == "alice@example.com"
        assert body["is_active"] is True
        assert "password" not in body

    async def test_duplicate_username(self, auth_client):
        payload = {"username": "bob", "email": "bob@example.com", "password": "pw"}
        await auth_client.post("/auth/register", json=payload)
        response = await auth_client.post("/auth/register", json={
            "username": "bob",
            "email": "other@example.com",
            "password": "pw",
        })
        assert response.status_code == 400

    async def test_duplicate_email(self, auth_client):
        await auth_client.post("/auth/register", json={
            "username": "carol",
            "email": "shared@example.com",
            "password": "pw",
        })
        response = await auth_client.post("/auth/register", json={
            "username": "dave",
            "email": "shared@example.com",
            "password": "pw",
        })
        assert response.status_code == 400

    async def test_missing_fields(self, auth_client):
        response = await auth_client.post("/auth/register", json={"username": "eve"})
        assert response.status_code == 422


class TestLogin:
    async def test_success(self, auth_client):
        await auth_client.post("/auth/register", json={
            "username": "frank",
            "email": "frank@example.com",
            "password": "mypassword",
        })
        response = await auth_client.post(
            "/auth/token",
            data={"username": "frank", "password": "mypassword"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password(self, auth_client):
        await auth_client.post("/auth/register", json={
            "username": "grace",
            "email": "grace@example.com",
            "password": "correct",
        })
        response = await auth_client.post(
            "/auth/token",
            data={"username": "grace", "password": "wrong"},
        )
        assert response.status_code == 401

    async def test_nonexistent_user(self, auth_client):
        response = await auth_client.post(
            "/auth/token",
            data={"username": "nobody", "password": "pw"},
        )
        assert response.status_code == 401
