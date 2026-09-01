import jwt
import os
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, UUID, String
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

load_dotenv()

app = FastAPI()

engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

bearer_scheme = HTTPBearer()

#Models
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key= True, default=uuid.uuid4)
    email= Column(String, unique= True, nullable= False,)
    hashed_password = Column(String, nullable = False)

# Schema
class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserCreate(BaseModel):
    email: EmailStr
    password: str

Base.metadata.create_all(bind=engine)

# Password helper functions
password_hash = PasswordHash.recommended()
def hash_password(password):
    return password_hash.hash(password)
def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes= int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 15)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.getenv('SECRET_KEY'), algorithm=os.getenv('ALGORITHM'))

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, key=os.getenv('SECRET_KEY'), algorithms= os.getenv('ALGORITHM'))
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    user = get_user_by_email(db, payload.get("email"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials")
    return user

# Routes
@app.post('/login')
def login(payload: UserCreate, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail = "Invalid credentials")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(access_token=token)

@app.post('/signup', response_model = UserResponse, status_code=status.HTTP_201_CREATED)
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

@app.get('/me', response_model=UserResponse)
def get_me(current_user = Depends(get_current_user)):
    return current_user

@app.get("/health")
def health_test():
    return {"message": "Application running successfully"}

