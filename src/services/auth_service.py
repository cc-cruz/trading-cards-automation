from datetime import datetime, timedelta
from typing import Optional
import jwt
import httpx
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from google.auth.transport import requests
from google.oauth2 import id_token
import json
import base64

from src.database import get_db
from src.models.user import User, UserType
from src.schemas.auth import TokenData, UserCreate, OAuthUserCreate

# Security configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # This is a secure key for development
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth configuration
import os
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id.apps.googleusercontent.com")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "your.apple.bundle.id")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_user(self, user: UserCreate) -> User:
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = self.get_password_hash(user.password)
        db_user = User(
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name,
            user_type=UserType.FREE
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Create default collection for new user
        from src.models.collection import Collection
        default_collection = Collection(
            name="My Cards",
            description="Default collection for your trading cards",
            user_id=db_user.id
        )
        self.db.add(default_collection)
        self.db.commit()
        
        return db_user

    def create_oauth_user(self, oauth_user: OAuthUserCreate) -> User:
        """Create a new user from OAuth provider data"""
        # Check if user already exists by OAuth ID
        oauth_id_field = f"{oauth_user.oauth_provider}_id"
        existing_user = self.db.query(User).filter(
            getattr(User, oauth_id_field) == oauth_user.oauth_id
        ).first()
        
        if existing_user:
            return existing_user
            
        # Check if user exists by email (link accounts)
        existing_email_user = self.db.query(User).filter(User.email == oauth_user.email).first()
        if existing_email_user:
            # Link OAuth account to existing user
            setattr(existing_email_user, oauth_id_field, oauth_user.oauth_id)
            if not existing_email_user.oauth_provider:
                existing_email_user.oauth_provider = oauth_user.oauth_provider
            if oauth_user.avatar_url and not existing_email_user.avatar_url:
                existing_email_user.avatar_url = oauth_user.avatar_url
            self.db.commit()
            self.db.refresh(existing_email_user)
            return existing_email_user

        # Create new OAuth user
        user_data = {
            "email": oauth_user.email,
            "full_name": oauth_user.full_name,
            "user_type": UserType.FREE,
            "oauth_provider": oauth_user.oauth_provider,
            "avatar_url": oauth_user.avatar_url,
            oauth_id_field: oauth_user.oauth_id
        }
        
        db_user = User(**user_data)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Create default collection for new user
        from src.models.collection import Collection
        default_collection = Collection(
            name="My Cards",
            description="Default collection for your trading cards",
            user_id=db_user.id
        )
        self.db.add(default_collection)
        self.db.commit()
        
        return db_user

    async def verify_google_token(self, token: str) -> dict:
        """Verify Google OAuth token and return user info"""
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), GOOGLE_CLIENT_ID
            )
            
            # Check if token is valid
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
                
            return {
                'id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False)
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Google token: {str(e)}"
            )

    async def verify_apple_token(self, id_token_str: str) -> dict:
        """Verify Apple ID token and return user info"""
        try:
            # For Apple, we need to verify the JWT token
            # This is a simplified version - in production you'd verify with Apple's keys
            header = jwt.get_unverified_header(id_token_str)
            payload = jwt.decode(id_token_str, options={"verify_signature": False})
            
            # In production, verify the signature with Apple's public keys
            # For now, we'll trust the token if it has the right structure
            
            if payload.get('iss') != 'https://appleid.apple.com':
                raise ValueError('Wrong issuer.')
                
            return {
                'id': payload['sub'],
                'email': payload.get('email'),
                'email_verified': payload.get('email_verified', False)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Apple token: {str(e)}"
            )

    async def authenticate_google_user(self, token: str) -> User:
        """Authenticate user with Google OAuth token"""
        google_user = await self.verify_google_token(token)
        
        if not google_user.get('email_verified'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google email not verified"
            )
        
        oauth_user = OAuthUserCreate(
            email=google_user['email'],
            full_name=google_user.get('name'),
            oauth_provider='google',
            oauth_id=google_user['id'],
            avatar_url=google_user.get('picture')
        )
        
        return self.create_oauth_user(oauth_user)

    async def authenticate_apple_user(self, id_token_str: str, user_data: Optional[dict] = None) -> User:
        """Authenticate user with Apple ID token"""
        apple_user = await self.verify_apple_token(id_token_str)
        
        # Apple only provides user info on first sign-in
        name = None
        if user_data and 'name' in user_data:
            name_parts = []
            if user_data['name'].get('firstName'):
                name_parts.append(user_data['name']['firstName'])
            if user_data['name'].get('lastName'):
                name_parts.append(user_data['name']['lastName'])
            name = ' '.join(name_parts) if name_parts else None
        
        oauth_user = OAuthUserCreate(
            email=apple_user['email'],
            full_name=name,
            oauth_provider='apple',
            oauth_id=apple_user['id']
        )
        
        return self.create_oauth_user(oauth_user)

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not user.password_hash:  # OAuth user trying to login with password
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token: str) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
            token_data = TokenData(email=email)
        except jwt.JWTError:
            raise credentials_exception
        user = self.db.query(User).filter(User.email == token_data.email).first()
        if user is None:
            raise credentials_exception
        return user

# Dependency
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db) 