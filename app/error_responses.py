from pydantic import BaseModel

class Message(BaseModel):
    detail: str

class RateLimitMessage(BaseModel):
    error : str

COMMON_RESPONSES = {
    401: {"model": Message, "description": "Not authenticated"},
    404: {"model": Message, "description": "Resource not found"},
    400: {"model": Message, "description": "Bad Request"},
    403: {"model": Message, "description": "Forbidden"},
    429: {"model": RateLimitMessage, "description": "Too many requests"}
}