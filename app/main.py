from app.auth.routes import jwt_auth
from app.auth.session_routes import session_auth
from fastapi import FastAPI

app = FastAPI()

app.include_router(jwt_auth)
app.include_router(session_auth)

@app.get("/health")
def health_test():
    return {"message": "Application running successfully"}
