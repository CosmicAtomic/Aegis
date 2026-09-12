import pytest
from app.security import hash_password

def test_password_is_hashed_not_plain():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"

@pytest.mark.asyncio
async def test_root(client):
    response = await client.get('/health')
    assert response.status_code == 200
    assert response.json() == {"message": "Application running successfully"}

@pytest.mark.asyncio
async def test_signup_success(client):
    response = await client.post('/jwt/signup', json= {
        "email": "test@example.com",
        "password": "supersecret123"
    })
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert "password" not in body and "hashed_password" not in body

@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    payload = {"email": "user1@example.com", "password": "supersecret123"}
    await client.post('/jwt/signup', json=payload)
    response = await client.post('/jwt/signup', json=payload)
    assert response.status_code == 400