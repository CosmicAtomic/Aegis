import jwt
import pytest
from app.dependencies import sessions
from app.main import app
from app.security import ALGORITHM, JWT_SECRET_KEY, hash_password
from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient

def make_expired_token(email):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    return jwt.encode(payload, key=JWT_SECRET_KEY,algorithm=ALGORITHM)

@pytest.fixture
async def client():
    transport = ASGITransport(app = app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture
async def registered_user(client):
    payload = {"email": "dope@example.com", "password": "supersecret123"}
    await client.post('/jwt/signup', json=payload)
    return payload

@pytest.fixture
async def logged_in_session(client, registered_user):
    response = await client.post('/session/login', json= registered_user)
    session_id = response.cookies.get("session_id")
    return session_id

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

# ------------ Test JWT Auth ---------
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

# ------- Test Session Auth----------
async def test_session_login_success(client, registered_user):
    response = await client.post('/session/login', json= registered_user)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_session_login_then_protected_route(client, logged_in_session):
    client.cookies.update({"session_id": logged_in_session})
    response = await client.get("/session/me")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_invalid_session_id_rejected(client):
    client.cookies.update({"session_id": "not.a.real.session.id"})
    response = await client.get('session/me')
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_expired_session_rejected(client, logged_in_session):
    sessions[logged_in_session]["created_at"] = datetime.now() - timedelta(minutes=31)
    client.cookies.update({"session_id": logged_in_session})
    response = await client.get('/session/me')
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_logout_removes_session(client, logged_in_session):
    client.cookies.update({"session_id": logged_in_session})
    await client.post("/session/logout")
    assert logged_in_session not in sessions 

    response = await client.get("/session/me")
    assert response.status_code == 401 

