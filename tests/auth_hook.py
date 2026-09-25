import schemathesis
import requests
import uuid

# ==============================================================================
# SCHEMATHESIS RUN INSTRUCTION
# ==============================================================================
# export SCHEMATHESIS_HOOKS="tests/auth_hook.py"
# 
# schemathesis run http://localhost:8000/openapi.json \
#   --exclude-path="/session/logout" \
#   --checks=not_a_server_error,response_schema_conformance
# ==============================================================================

TEST_EMAIL = f"schemathesis_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "Password123!"
AUTH_DATA = {}

def get_cached_auth():
    global AUTH_DATA
    if not AUTH_DATA:
        requests.post(
            "http://localhost:8000/jwt/signup",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        jwt_resp = requests.post(
            "http://localhost:8000/jwt/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = jwt_resp.json().get("access_token")

        session_resp = requests.post(
            "http://localhost:8000/session/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        session_id = session_resp.cookies.get("session_id")
        csrf_token = session_resp.cookies.get("csrfToken")

        AUTH_DATA = {
            "jwt": f"Bearer {token}",
            "session_id": session_id,
            "csrf_token": csrf_token
        }
    return AUTH_DATA

@schemathesis.hook
def before_call(ctx, case, kwargs):
    auth = get_cached_auth()
    
    if case.headers is None:
        case.headers = {}

    # Check the path of the specific endpoint being tested
    if "/jwt/" in case.path:
        case.headers["Authorization"] = auth["jwt"]
        
    elif "/session/" in case.path:
        case.headers["Cookie"] = f"session_id={auth['session_id']}; csrfToken={auth['csrf_token']}"
        if case.method.upper() == "POST":
            case.headers["X-CSRF-Token"] = auth["csrf_token"]
