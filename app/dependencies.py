import secrets
import uuid
from app.config import settings
from app.database import SessionLocal
from app.security import decode_access_token
from app.services import get_user_by_email, get_user_by_id
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer()
sessions: dict[str, dict] = {}  # In-memory session storage

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    user = get_user_by_email(db, payload.get("email"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    return user

def get_session_user(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id is None or session_id not in sessions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    session_data = sessions[session_id]
    elapsed = datetime.now() - session_data["created_at"]
    if elapsed > timedelta(minutes=settings.SESSION_EXPIRE_MINUTES):
        del sessions[session_id]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user_id = uuid.UUID(session_data["user_id"])
    user = get_user_by_id(db, user_id)
    return user

def verify_csrf_token(request: Request):
    cookie_token = request.cookies.get("csrfToken")
    header_token = request.headers.get('X-CSRF-Token')
    if not cookie_token or not header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")
    return True