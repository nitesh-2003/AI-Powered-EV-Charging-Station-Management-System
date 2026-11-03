from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Schema for returning JWT access token upon successful authentication."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for validated JWT payload claims."""
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
