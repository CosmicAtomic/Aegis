import jwt
import pytest
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