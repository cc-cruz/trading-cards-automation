from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text
from sqlalchemy.sql import func
import enum
from sqlalchemy.orm import relationship
import uuid

from src.database import Base

class UserType(enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Made nullable for OAuth users
    full_name = Column(String)
    user_type = Column(Enum(UserType), default=UserType.FREE)
    is_active = Column(Boolean, default=True)
    
    # OAuth fields
    google_id = Column(String, unique=True, nullable=True, index=True)
    apple_id = Column(String, unique=True, nullable=True, index=True)
    oauth_provider = Column(String, nullable=True)  # 'google', 'apple', or None for email/password
    avatar_url = Column(String, nullable=True)
    
    # Stripe fields
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive")  # active, canceled, past_due, etc.
    subscription_plan = Column(String, default="free")  # free, pro
    usage_count = Column(Integer, default=0)
    usage_reset_date = Column(DateTime, default=func.now())
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships - using string references to avoid circular imports
    collections = relationship("Collection", back_populates="user", lazy="dynamic")
    subscription = relationship("Subscription", back_populates="user", uselist=False) 