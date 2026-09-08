from app.auth.google_routes import google_auth
from app.config import settings
from app.auth.oauth_routes import github_auth
from app.auth.routes import jwt_auth
from app.auth.session_routes import session_auth
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY, same_site="lax", https_only=False)

app.include_router(jwt_auth)
app.include_router(session_auth)
app.include_router(github_auth)
app.include_router(google_auth)

@app.get("/health")
def health_test():
    return {"message": "Application running successfully"}
