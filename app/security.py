import jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

load_dotenv()

JWT_SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 15)

password_hash = PasswordHash.recommended()

def hash_password(password):
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes= int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, key=JWT_SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token):
    return jwt.decode(token, key=JWT_SECRET_KEY, algorithms= ALGORITHM)