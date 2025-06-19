from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    user_type: str = "collector"

class UserResponse(UserBase):
    id: str
    user_type: str
    created_at: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

# OAuth schemas
class GoogleOAuthRequest(BaseModel):
    token: str  # Google OAuth token from frontend

class AppleOAuthRequest(BaseModel):
    code: str  # Apple authorization code
    id_token: str  # Apple ID token
    user: Optional[dict] = None  # Apple user info (only provided on first sign-in)

class OAuthUserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    oauth_provider: str  # 'google' or 'apple'
    oauth_id: str  # Provider-specific user ID
    avatar_url: Optional[str] = None

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True 