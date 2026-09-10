from app.dependencies import get_db, get_session_user, sessions, verify_csrf_token
from app.schema import UserCreate, UserResponse
from app.security import verify_password, generate_csrf_token
from app.services import get_user_by_email
from datetime import datetime
from fastapi import APIRouter, Depends,  HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from uuid import uuid4

session_auth = APIRouter(prefix='/session')

@session_auth.post('/login')
def login(payload: UserCreate, response: Response, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "Invalid credentials")
    session_id = str(uuid4())
    sessions[session_id] = {
         "user_id": str(user.id), 
         "email": user.email,
         "created_at": datetime.now()
    }
    response.set_cookie(
          key="session_id",
          value= session_id,
          httponly=True,
          secure= False,
          samesite= "lax"
    )
    csrf_token = generate_csrf_token()
    response.set_cookie(
         key='csrfToken',
         value=csrf_token,
         httponly=False,
         secure=False,
         samesite='lax',
         max_age=3600
    )
    return {"message": "Logged in"}

@session_auth.get('/me',  response_model=UserResponse)
def get_me(user = Depends(get_session_user)):
    return user
            
@session_auth.post('/logout', dependencies=[Depends(verify_csrf_token)])
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]
    response.delete_cookie("session_id")
    response.delete_cookie("csrfToken")
    return {"message": "Logged out"}
      
