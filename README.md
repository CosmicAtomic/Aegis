# Auth Service

A FastAPI authentication service demonstrating two authentication approaches:

- JWT bearer-token authentication
- Cookie-based session authentication

## Features

- User signup with Argon2 password hashing
- JWT login and protected user endpoint
- Cookie-based session login, logout, and protected user endpoint
- JWT and session expiration checks
- Environment-based application settings
- Automated tests for both authentication flows

## Project Structure

```text
app/
├── auth/
│   ├── routes.py          # JWT authentication routes
│   └── session_routes.py  # Session authentication routes
├── config.py              # Environment-based settings
├── database.py            # SQLAlchemy database setup
├── dependencies.py        # Database and authentication dependencies
├── main.py                # FastAPI application
├── models.py              # Database models
├── schema.py              # Pydantic schemas
├── security.py            # Password hashing and JWT helpers
└── services.py            # Database service functions

tests/
└── test_auth.py           # Authentication tests
```

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic Settings
- PyJWT
- pwdlib with Argon2 support
- pytest, pytest-asyncio, and httpx

Install the dependencies with:

```bash
pip install fastapi uvicorn sqlalchemy pydantic-settings pyjwt "pwdlib[argon2]" python-dotenv pytest pytest-asyncio httpx email-validator
```

## Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./auth.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Do not commit `.env` or real secret keys.

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

JWTs expire according to `ACCESS_TOKEN_EXPIRE_MINUTES`.

### Session Authentication

| Method | Endpoint          | Purpose                       |
| ------ | ----------------- | ----------------------------- |
| POST   | `/session/login`  | Create a cookie-based session |
| GET    | `/session/me`     | Return the authenticated user |
| POST   | `/session/logout` | Delete the current session    |

The session identifier is stored in an HTTP-only cookie. The server rejects sessions after 30 minutes. Session data is currently stored in memory, so sessions are lost when the application restarts and are not suitable for a multi-instance production deployment.

The session cookie currently uses `secure=True`, so it is sent only over HTTPS. For local HTTP development, the cookie configuration must be adjusted or the application must be run over HTTPS.

## Run Tests

Run the full test suite with:

```bash
python -m pytest -q
```

The tests use a separate SQLite database and override the application database dependency so they do not use the development database.

## Current Limitations

- Session storage is in memory rather than Redis or a database-backed session store.
- CSRF protection has not been added for cookie-authenticated state-changing requests.
- The session expiration duration is currently hardcoded to 30 minutes.
- Production deployments should use HTTPS and a strong secret from a secure secret store.
