from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
import uuid

from ..database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String, unique=True)
    stripe_customer_id = Column(String)
    plan_type = Column(String, nullable=False, default='free')  # 'free', 'pro'
    status = Column(String, nullable=False, default='active')  # 'active', 'cancelled', 'expired'
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscription") 