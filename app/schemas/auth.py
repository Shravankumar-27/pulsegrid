from pydantic import BaseModel


class LoginRequest(BaseModel):
    telegram_user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"