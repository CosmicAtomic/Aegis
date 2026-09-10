import httpx2
from app.config import settings
from app.dependencies import get_db
from app.models import User
from app.schema import Token
from app.security import create_access_token
from app.services import get_user_by_github_id
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

GITHUB_CLIENT_ID = settings.GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET = settings.GITHUB_CLIENT_SECRET
REDIRECT_URI = "http://localhost:8000/github/callback"

github_auth = APIRouter(prefix="/github")

@github_auth.get('/login')
def login_via_github():
    github_authorize_url =(
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=read:user user:email"
    )
    return RedirectResponse(github_authorize_url)

@github_auth.get('/callback')
async def github_callback(code, db: Session = Depends(get_db)):
    async with httpx2.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret" : GITHUB_CLIENT_SECRET,
                "code" : code
            },
            headers={"Accept": "application/json"}
        )
        token_response.raise_for_status()

        token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(status_code=400, detail=f"GitHub OAuth Error: {token_data.get('error_description', token_data['error'])}")
        access_token = token_data["access_token"]
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token.")

        user_response = await client.get(
            "https://api.github.com/user",
            headers= {"Authorization": f"Bearer {access_token}"}
        )
        user_response.raise_for_status()
        github_user = user_response.json()
        
        user = get_user_by_github_id(db, github_user["id"])
        if not user:
            user = User(
                github_id = github_user["id"],
                username = github_user["login"],
                email= github_user.get("email")   
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return Token(access_token=token)


