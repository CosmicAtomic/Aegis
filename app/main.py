from app.auth.google_routes import google_auth
from app.auth.oauth_routes import github_auth
from app.auth.routes import jwt_auth
from app.auth.session_routes import session_auth
from app.config import settings
from app.limiter import limiter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = []# Add the frontend origin here when a separate frontend is introduced.
app.add_middleware(
    CORSMiddleware, 
    allow_origins= origins,
    allow_methods= ["*"],
    allow_headers= ["*"],
    allow_credentials= True
)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY, same_site="lax", https_only=False)

app.include_router(jwt_auth)
app.include_router(session_auth)
app.include_router(github_auth)
app.include_router(google_auth)

@app.get("/health")
def health_test():
    return {"message": "Application running successfully"}
