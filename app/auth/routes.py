from app.dependencies import get_current_user, get_db
from app.models import User
from app.security import create_access_token, hash_password, verify_password 
from app.services import check_rate_limit, get_user_by_email
from app.schema import Token, UserCreate, UserResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

jwt_auth = APIRouter(prefix='/jwt')

@jwt_auth.post('/login')
def login(payload: UserCreate, db: Session = Depends(get_db)):
    check_rate_limit(payload.email)
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail = "Invalid credentials")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token)

@jwt_auth.post('/signup', response_model = UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    new_user = User(
        email = payload.email,
        hashed_password = hash_password(payload.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@jwt_auth.get('/me', response_model=UserResponse)
def get_me(current_user = Depends(get_current_user)):
    return current_user
