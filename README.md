# Aegis

A FastAPI authentication service providing multiple authentication approaches:

- JWT bearer-token authentication
- Cookie-based session authentication
- Google OAuth authentication
- GitHub OAuth authentication

## Features

- User signup with Argon2 password hashing
- JWT login and protected user endpoint
- Cookie-based session login, logout, and protected user endpoint
- JWT and session expiration checks
- CSRF protection for session logout
- Rate limiting for JWT and session login
- OAuth callbacks with provider error handling
- Alembic database migrations
- Environment-based application settings
- Automated tests organized by authentication flow

## Project Structure

```text
app/
├── auth/
│   ├── google_routes.py     # Google OAuth routes
│   ├── oauth_routes.py      # GitHub OAuth routes
│   ├── routes.py            # JWT authentication routes
│   └── session_routes.py    # Session authentication routes
├── config.py                # Environment-based settings
├── database.py              # SQLAlchemy database setup
├── dependencies.py          # Database and authentication dependencies
├── limiter.py               # SlowAPI rate limiter
├── main.py                  # FastAPI application
├── models.py                # Database models
├── schema.py                # Pydantic schemas
├── security.py              # Password hashing and JWT helpers
└── services.py              # Database service functions

alembic/                     # Database migration configuration and versions
tests/
├── conftest.py              # Shared pytest fixtures
├── test_auth_github.py      # GitHub OAuth tests
├── test_auth_google.py      # Google OAuth tests
├── test_auth_jwt.py         # JWT tests
├── test_auth_session.py     # Session and CSRF tests
├── test_health_signup.py    # Health and signup tests
└── test_rate_limit.py       # Rate-limit tests
```

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic Settings
- PyJWT
- pwdlib with Argon2 support
- Authlib
- SlowAPI
- pytest, pytest-asyncio, and httpx2

Install the dependencies with:

```bash
pip install fastapi uvicorn sqlalchemy alembic pydantic-settings pyjwt "pwdlib[argon2]" python-dotenv authlib slowapi pytest pytest-asyncio httpx2 email-validator
```

## Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./auth.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
SESSION_SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SESSION_EXPIRE_MINUTES=30
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Do not commit `.env` or real secret keys.

Configure the OAuth provider callback URLs as follows for local development:

- Google: `http://localhost:8000/google/callback`
- GitHub: `http://localhost:8000/github/callback`

## Run the Application

Start the development server with:

```bash
uvicorn app.main:app --reload
```

The service will be available at:

- Health check: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

## Authentication Endpoints

### JWT Authentication

| Method | Endpoint      | Purpose                       |
| ------ | ------------- | ----------------------------- |
| POST   | `/jwt/signup` | Create a user account         |
| POST   | `/jwt/login`  | Return a JWT access token     |
| GET    | `/jwt/me`     | Return the authenticated user |

To call `/jwt/me`, send the token as a bearer token:

```text
Authorization: Bearer <access_token>
```

JWTs expire according to `ACCESS_TOKEN_EXPIRE_MINUTES`. JWT login is limited to five requests per minute per client IP.

### Session Authentication

| Method | Endpoint          | Purpose                       |
| ------ | ----------------- | ----------------------------- |
| POST   | `/session/login`  | Create a cookie-based session |
| GET    | `/session/me`     | Return the authenticated user |
| POST   | `/session/logout` | Delete the current session    |

The session identifier is stored in an HTTP-only cookie. The server rejects sessions after the configured `SESSION_EXPIRE_MINUTES` period. Session data is currently stored in memory, so sessions are lost when the application restarts and are not suitable for a multi-instance production deployment.

Session login is limited to five requests per minute per client IP. Logout requires the `X-CSRF-Token` header to match the non-HTTP-only `csrfToken` cookie.

The session cookies currently use `secure=False` for local HTTP development. Set secure cookies and serve the application over HTTPS in production.

### OAuth Authentication

| Method | Endpoint           | Purpose                     |
| ------ | ------------------ | --------------------------- |
| GET    | `/google/login`    | Start Google OAuth login    |
| GET    | `/google/callback` | Complete Google OAuth login |
| GET    | `/github/login`    | Start GitHub OAuth login    |
| GET    | `/github/callback` | Complete GitHub OAuth login |

Successful OAuth callbacks return the same JWT response format as `/jwt/login`. Provider failures and invalid provider responses return `400` responses.

## Database Migrations

Apply existing migrations with:

```bash
alembic upgrade head
```

Create a new migration after changing the SQLAlchemy models with:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

## Run Tests

Run the full test suite with:

```bash
python -m pytest -q
```

The tests use a separate SQLite database and shared fixtures so they do not use the development database. SlowAPI in-memory state is reset between tests.

## Current Limitations

- Session storage is in memory rather than Redis or a database-backed session store.
- The rate limiter uses in-memory storage and is not suitable for coordinated multi-instance deployments.
- OAuth callback URLs are currently configured for local development and should be externalized for deployment.
- Production deployments should use HTTPS and strong secrets from a secure secret store.
