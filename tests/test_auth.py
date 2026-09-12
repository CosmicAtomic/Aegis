import jwt
import pytest
import time
from app.dependencies import sessions
from app.main import app
from app.security import ALGORITHM, JWT_SECRET_KEY, hash_password
from datetime import datetime, timedelta, timezone
from httpx2 import ASGITransport, AsyncClient

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

@pytest.fixture(autouse=True)
def reset_rate_limiter(request):
    """Resets the slowapi rate limiter memory after every test."""
    yield
    # Access your FastAPI app instance via your client fixture
    if hasattr(request.node, "config"):
        if hasattr(app.state, "limiter"):
            app.state.limiter._storage.reset()

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
    csrf_token = client.cookies.get("csrfToken")
    await client.post("/session/logout", headers={"X-CSRF-Token": csrf_token})
    assert logged_in_session not in sessions 

    response = await client.get("/session/me")
    assert response.status_code == 401 

@pytest.mark.asyncio
async def test_csrf_valid_token_success(client, logged_in_session):
    client.cookies.update({"session_id": logged_in_session})
    csrf_token = client.cookies.get("csrfToken")
    assert csrf_token is not None, "CSRF cookie was not injected by the server"
    response = await client.post(
        "session/logout",
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_missing_csrf_token_rejected(client, logged_in_session):
    client.cookies.update({"session_id": logged_in_session})
    response = await client.post("session/logout")
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF token missing"}

@pytest.mark.asyncio
async def test_invalid_csrf_token_rejected(client, logged_in_session):
    client.cookies.update({"session_id": logged_in_session})
    response = await client.post(
        "session/logout",
        headers= {"X-CSRF-Token": "wrong-token"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF token mismatch"}

#-------Test Rate limit ---------
@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold(client):
    spam_payload = {"email": "spam@example.com", "password": "guessed_password"}
    for _ in range(5):
        await client.post('session/login', json= spam_payload)
        await client.post('jwt/login', json= spam_payload)
    jwt_response = await client.post('jwt/login', json= spam_payload)
    session_response = await client.post('session/login', json= spam_payload)
    assert session_response.status_code == 429
    assert jwt_response.status_code == 429

async def test_rate_limit_runs_under_window(client):
    spam_payload = {"email": "spam@example.com", "password": "guessed_password"}
    for _ in range(4):
        jwt_response = await client.post('jwt/login', json= spam_payload)
        assert jwt_response.status_code != 429
    for _ in range(4):
        session_response = await client.post('session/login', json= spam_payload)
        assert session_response.status_code != 429

async def test_rate_limit_resets_after_window(client, monkeypatch):
    spam_payload = {"email": "spam@example.com", "password": "guessed_password"}
    for _ in range(5):
        await client.post('jwt/login', json= spam_payload)
        await client.post('session/login', json= spam_payload)
    jwt_response = await client.post('jwt/login', json= spam_payload)
    assert jwt_response.status_code == 429
    session_response = await client.post('session/login', json= spam_payload)
    assert session_response.status_code == 429

    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 61)

    jwt_response = await client.post('jwt/login', json= spam_payload)
    assert jwt_response.status_code != 429
    session_response = await client.post('session/login', json= spam_payload)
    assert session_response.status_code != 429

# ------Test Github auth-----
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_github_callback_success(client):
    fake_token = {"access_token": "fake_token_123"}
    fake_profile = {"id": 999, "login": "testuser", "email": "test@github.com"}
    token_response = MagicMock()
    token_response.json.return_value = fake_token
    profile_response = MagicMock()
    profile_response.json.return_value = fake_profile
    github_client = MagicMock()
    github_client.__aenter__ = AsyncMock(return_value=github_client)
    github_client.__aexit__ = AsyncMock(return_value=None)
    github_client.post = AsyncMock(return_value=token_response)
    github_client.get = AsyncMock(return_value=profile_response)

    with patch("app.auth.oauth_routes.httpx2.AsyncClient", return_value=github_client):

        response = await client.get("/github/callback?code=fakecode&state=fakestate")

    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_github_token_exchange_failure(client):
    github_client = MagicMock()
    github_client.__aenter__ = AsyncMock(return_value=github_client)
    github_client.__aexit__ = AsyncMock(return_value=None)
    github_client.post = AsyncMock(side_effect=Exception("bad code"))

    with patch("app.auth.oauth_routes.httpx2.AsyncClient", return_value=github_client):
        response = await client.get("/github/callback?code=badcode&state=fakestate")

    assert response.status_code == 400

@pytest.mark.asyncio
async def test_github_profile_fetch_bad_shape(client):
    fake_token = {"access_token": "fake_token_123"}
    token_response = MagicMock()
    token_response.json.return_value = fake_token
    profile_response = MagicMock()
    profile_response.json.return_value = {}
    github_client = MagicMock()
    github_client.__aenter__ = AsyncMock(return_value=github_client)
    github_client.__aexit__ = AsyncMock(return_value=None)
    github_client.post = AsyncMock(return_value=token_response)
    github_client.get = AsyncMock(return_value=profile_response)

    with patch("app.auth.oauth_routes.httpx2.AsyncClient", return_value=github_client):

        response = await client.get("/github/callback?code=fakecode&state=fakestate")

    assert response.status_code == 400

#----Test Google Auth----
@pytest.mark.asyncio
async def test_google_callback_success(client):
    fake_token = {
        "access_token": "fake_token_123",
        "userinfo": {"sub": "google-999", "name": "Test User", "email": "test@gmail.com"},
    }

    with patch("app.auth.google_routes.oauth.google.authorize_access_token", new=AsyncMock(return_value=fake_token)):
        response = await client.get("/google/callback?code=fakecode&state=fakestate")

    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_google_invalid_token_rejected(client):
    with patch("app.auth.google_routes.oauth.google.authorize_access_token", new=AsyncMock(side_effect=Exception("state mismatch"))):
        response = await client.get("/google/callback?code=badcode&state=wrongstate")

    assert response.status_code == 400