import pytest
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
