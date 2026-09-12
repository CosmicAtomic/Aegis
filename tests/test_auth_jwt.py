import pytest
from tests.conftest import make_expired_token

@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    response = await client.post('jwt/login', json=registered_user)
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    bad_payload = {"email": registered_user["email"], "password": "wrong.password"}
    response = await client.post('jwt/login', json= bad_payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_expired_token_rejected(client, registered_user):
    expired_token = make_expired_token(registered_user["email"])
    response = await client.get('jwt/me', headers= {"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_routes_no_token(client):
    response = await client.get('jwt/me')
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_routes_garbage_token(client):
    response = await client.get('jwt/me', headers= {"Authorization": f"Bearer not.a.token"})
    assert response.status_code == 401