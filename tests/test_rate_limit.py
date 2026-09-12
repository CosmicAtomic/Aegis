import time
import pytest 

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