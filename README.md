# Aegis

Aegis is a FastAPI authentication service that exposes four authentication flows:

- Email/password authentication with Argon2 password hashing
- JWT bearer-token authentication
- Cookie-based server-side sessions with CSRF-protected logout
- Google and GitHub OAuth login

The service uses SQLAlchemy for persistence, Alembic for schema migrations, Pydantic Settings for environment configuration, and SlowAPI for login rate limiting.

## Features

- User signup and password login
- Protected `GET /jwt/me` endpoint
- Protected `GET /session/me` endpoint
- JWT expiration validation
- In-memory session expiration and invalidation
- CSRF validation for session logout
- Five login attempts per minute per client IP for both login endpoints
- Google OpenID Connect login
- GitHub OAuth login
- FastAPI OpenAPI documentation at `/docs`
- Async HTTP integration tests using `httpx2` and `ASGITransport`

## Requirements

- Python 3.10 or newer
- A database supported by the configured SQLAlchemy URL
- OAuth applications only if Google or GitHub login is required

The repository pins its Python dependencies in [requirements.txt](requirements.txt). The dependency set includes FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, PyJWT, `pwdlib[argon2]`, Authlib, SlowAPI, pytest, `pytest-asyncio`, `httpx2`, and Schemathesis-related performance tooling.

## Local Setup

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a `.env` file in the repository root. Pydantic Settings loads this file when `app.config` is imported.

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/aegis
JWT_SECRET_KEY=replace-with-a-long-random-secret
SESSION_SECRET_KEY=replace-with-a-different-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SESSION_EXPIRE_MINUTES=30
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

All seven secret/database/provider variables are required at import time. `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, and `SESSION_EXPIRE_MINUTES` have defaults, but defining them explicitly makes deployments easier to audit. Never commit `.env` or real credentials.

## Configuration Reference

| Variable                      | Required | Default | Purpose                                             |
| ----------------------------- | -------- | ------- | --------------------------------------------------- |
| `DATABASE_URL`                | Yes      | None    | SQLAlchemy database connection URL                  |
| `JWT_SECRET_KEY`              | Yes      | None    | Signs and verifies JWTs                             |
| `SESSION_SECRET_KEY`          | Yes      | None    | Signs Starlette OAuth state/session middleware data |
| `ALGORITHM`                   | No       | `HS256` | JWT signing algorithm                               |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `30`    | JWT lifetime                                        |
| `SESSION_EXPIRE_MINUTES`      | No       | `30`    | Application session lifetime                        |
| `GITHUB_CLIENT_ID`            | Yes      | None    | GitHub OAuth client ID                              |
| `GITHUB_CLIENT_SECRET`        | Yes      | None    | GitHub OAuth client secret                          |
| `GOOGLE_CLIENT_ID`            | Yes      | None    | Google OAuth client ID                              |
| `GOOGLE_CLIENT_SECRET`        | Yes      | None    | Google OAuth client secret                          |

## Database

The application defines one SQLAlchemy model, `User`, mapped to the `users` table:

| Column            | Type   | Nullable | Notes                                                                        |
| ----------------- | ------ | -------- | ---------------------------------------------------------------------------- |
| `id`              | UUID   | No       | Primary key, generated with `uuid.uuid4`                                     |
| `email`           | String | Yes      | Unique; required for password signup but nullable for some provider profiles |
| `hashed_password` | String | Yes      | Argon2 hash; null for OAuth-only accounts                                    |
| `github_id`       | String | Yes      | Unique and indexed GitHub provider identifier                                |
| `google_id`       | String | Yes      | Unique Google provider identifier                                            |
| `username`        | String | Yes      | Provider profile name/login                                                  |

### Migration commands

The Alembic environment reads `DATABASE_URL` from application settings and uses the SQLAlchemy metadata from `app.models` for autogeneration.

```bash
alembic current
alembic history
alembic upgrade head
alembic revision --autogenerate -m "describe the schema change"
```

**Fresh-database warning:** the first committed revision, `84e38669bc41`, contains no table-creation operation. Later revisions alter the `users` table, so the committed migration chain cannot currently bootstrap a brand-new empty database. Verify or repair the initial migration before using Alembic as the provisioning path for a new environment. The automated tests do not exercise this chain; they create tables directly from `Base.metadata` in SQLite.

## Run the API

Start the development server from the repository root:

```bash
uvicorn app.main:app --reload
```

The default local URLs are:

- Health check: <http://127.0.0.1:8000/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

The health endpoint returns:

```json
{ "message": "Application running successfully" }
```

## API Reference

All JSON request bodies that contain an email use Pydantic's `EmailStr` validation. Invalid email values receive FastAPI's standard `422` validation response. Successful user responses contain only `id` and `email`; passwords and provider identifiers are not returned.

### Health

`GET /health` requires no authentication and returns `200` when the application is running.

### Password and JWT authentication

#### `POST /jwt/signup`

Creates a password-backed user. Request body:

```json
{
  "email": "user@example.com",
  "password": "supersecret123"
}
```

Success: `201 Created`

```json
{
  "id": "3f8c2f28-7e18-4a31-a0bc-1b7d3a4b9e5e",
  "email": "user@example.com"
}
```

An existing email returns `400` with `{"detail":"Email already exists"}`.

#### `POST /jwt/login`

Accepts the same body as signup. Success returns `200`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Unknown users and incorrect passwords return `401` with `Invalid credentials`. This endpoint is limited to five requests per minute per client IP.

#### `GET /jwt/me`

Requires an HTTP Bearer token:

```http
Authorization: Bearer <jwt>
```

Valid, unexpired tokens return the authenticated user's `id` and `email`. Missing, malformed, expired, or unresolvable tokens return `401`.

JWT payloads include `sub`, `email`, and `exp`. The current dependency verifies that `sub` exists, then resolves the user by the token's `email` claim.

Example:

```bash
curl http://127.0.0.1:8000/jwt/me \
  -H "Authorization: Bearer <jwt>"
```

### Cookie sessions

#### `POST /session/login`

Accepts the same email/password body as JWT login. Success returns:

```json
{ "message": "Logged in" }
```

The response sets two cookies:

- `session_id`: HTTP-only session identifier
- `csrfToken`: JavaScript-readable CSRF token with a one-hour cookie lifetime

Session login is limited to five requests per minute per client IP.

#### `GET /session/me`

Requires the `session_id` cookie. A valid session returns the authenticated user's public response. Missing, unknown, expired, or deleted sessions return `401`.

#### `POST /session/logout`

Requires both the session cookies and an `X-CSRF-Token` header whose value matches the `csrfToken` cookie:

```bash
curl -X POST http://127.0.0.1:8000/session/logout \
  -H "X-CSRF-Token: <csrf-token>" \
  -b "session_id=<session-id>; csrfToken=<csrf-token>"
```

Success deletes the in-memory session and both cookies, returning `{"message":"Logged out"}`. A missing CSRF value returns `403` with `CSRF token missing`; a mismatch returns `403` with `CSRF token mismatch`.

### Google OAuth

1. Open `GET /google/login` in a browser.
2. The service redirects to Google using the OpenID Connect metadata endpoint and requests `openid email profile`.
3. Google redirects to `GET /google/callback`.
4. The callback links an existing account by Google ID or email, creates a new provider account when needed, and returns the standard JWT response.

The local callback URL is hard-coded as `http://localhost:8000/google/callback`. Register that exact URL in the Google OAuth client for local development. Provider failures or missing `userinfo.sub` return `400`.

### GitHub OAuth

1. Open `GET /github/login` in a browser.
2. The service redirects to GitHub requesting `read:user user:email`.
3. GitHub redirects to `GET /github/callback?code=<code>`.
4. The service exchanges the code, fetches the GitHub profile, creates or finds the user by GitHub ID, and returns the standard JWT response.

The local callback URL is hard-coded as `http://localhost:8000/github/callback`. Provider failures, missing access tokens, or profiles without both `id` and `login` return `400`.

The implementation currently uses the profile's `email` field directly; it does not make a separate GitHub `/user/emails` request despite requesting the `user:email` scope.

## Security and Deployment Notes

The current configuration is suitable for local development and needs hardening before production:

- Sessions are stored in the process-local `sessions` dictionary. They disappear on restart and are not shared between workers or instances. Use a shared store such as Redis for a multi-instance deployment.
- SlowAPI's default in-memory storage is also process-local, so rate limits are not coordinated across instances.
- Session cookies and Starlette's `SessionMiddleware` currently use `secure=False`; deploy behind HTTPS and enable secure cookies in production.
- OAuth callback URLs are hard-coded to localhost and should be externalized for deployed environments.
- CORS is enabled with credentials but `allow_origins` is currently empty, so no browser frontend origin is allowed until configured.
- Use distinct, high-entropy JWT and session secrets, supplied through a secret manager rather than source control.
- There is no password reset, email verification, refresh-token rotation, JWT revocation, account deletion, or JWT logout endpoint.

## Testing

Run the complete test suite:

```bash
python -m pytest -q
```

The current baseline contains 25 tests covering:

- Health and password signup
- Duplicate email rejection
- Password login and invalid credentials
- Missing, malformed, and expired JWTs
- Session creation, access, expiry, and logout
- CSRF success, missing-token, and mismatch cases
- Google and GitHub OAuth success/error handling with mocked provider calls
- Login rate limiting and window reset behavior

Tests use `tests/conftest.py` to create an isolated SQLite database with `Base.metadata.create_all()` and override the application's `get_db` dependency. They do not use the configured development database or run Alembic migrations. The root `conftest.py` also defines database setup, so fixture behavior should be kept in mind when extending the suite.

## Optional Schema Testing

`performance/schemathesis_hook.py` contains a Schemathesis hook that prepares JWT and session credentials for requests against the live OpenAPI document.

Start the API first, then run:

```bash
set SCHEMATHESIS_HOOKS=performance/schemathesis_hook.py
schemathesis run http://localhost:8000/openapi.json --exclude-path="/session/logout" --checks=not_a_server_error,response_schema_conformance
```

In PowerShell, set the hook with:

```powershell
$env:SCHEMATHESIS_HOOKS = "performance/schemathesis_hook.py"
```

The hook creates a temporary user and caches JWT/session credentials for the run. It intentionally excludes `/session/logout` because that endpoint mutates authentication state and requires CSRF coordination.

## Project Layout

```text
app/
├── main.py                 # FastAPI app, middleware, routers, health endpoint
├── config.py               # Pydantic Settings and .env loading
├── database.py             # SQLAlchemy engine, session factory, Base
├── models.py               # User ORM model
├── schema.py               # Request and response models
├── security.py             # Argon2, JWT, and CSRF helpers
├── dependencies.py         # Database, JWT, session, and CSRF dependencies
├── services.py             # User lookup helpers
├── limiter.py              # SlowAPI limiter
├── error_responses.py      # Shared OpenAPI error response definitions
└── auth/
    ├── routes.py           # Signup, JWT login, and /jwt/me
    ├── session_routes.py   # Session login, /session/me, and logout
    ├── google_routes.py    # Google OAuth
    └── oauth_routes.py     # GitHub OAuth
alembic/
├── env.py                  # Migration runtime configuration
└── versions/               # Versioned schema revisions
tests/                       # Async endpoint and behavior tests
performance/                # Schemathesis live-schema hook
```
