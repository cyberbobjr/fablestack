from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    response = await async_client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data

@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient):
    # Register first
    email = f"login_{uuid4()}@example.com"
    await async_client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Login User"
    })
    
    # Login
    response = await async_client.post("/api/auth/token", data={
        "username": email,
        "password": "Password123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    response = await async_client.post("/api/auth/token", data={
        "username": "wrong@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
