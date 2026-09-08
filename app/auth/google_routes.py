from app.config import settings
from app.dependencies import get_db
from app.models import User
from app.schema import Token
from app.security import create_access_token
from app.services import get_user_by_google_id
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET

# NOTE: Use http://localhost:8000/google/login while testing

google_auth= APIRouter(prefix="/google")

oauth = OAuth()
oauth.register(
    name= "google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

@google_auth.get("/login")
async def login_via_google(request: Request):
    redirect_uri= "http://localhost:8000/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@google_auth.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    google_user = token.get("userinfo")
    if not google_user or not google_user.get("sub"):
        raise HTTPException(status_code=400, detail="Google did not return valid user information.")
    user = get_user_by_google_id(db, google_user["sub"])
    if not user:
        user = db.query(User).filter(User.email == google_user.get("email")).first()
        if user:
            user.google_id = google_user["sub"]
            db.commit()
        else:
            user = User(
                google_id=google_user["sub"],
                username=google_user.get("name"),
                email=google_user.get("email")   
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token)
