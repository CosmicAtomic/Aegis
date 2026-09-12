import pytest
from unittest.mock import AsyncMock, patch

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