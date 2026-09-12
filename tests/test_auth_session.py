import pytest
from app.dependencies import sessions
from datetime import datetime, timedelta

@pytest.mark.asyncio
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

# Test CSRF 
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
