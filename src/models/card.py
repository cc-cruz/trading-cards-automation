from sqlalchemy import Column, String, DateTime, ForeignKey, func, JSON, Boolean
from sqlalchemy.orm import relationship
import uuid

from src.database import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"))
    player_name = Column(String)
    set_name = Column(String)
    year = Column(String)
    card_number = Column(String)
    parallel = Column(String)
    manufacturer = Column(String)
    features = Column(JSON)
    graded = Column(Boolean)
    grade = Column(String)
    grading_company = Column(String)
    cert_number = Column(String)
    price_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships - using string references to avoid circular imports
    images = relationship("CardImage", back_populates="card", lazy="dynamic")
    collection = relationship("Collection", back_populates="cards")

class CardImage(Base):
    __tablename__ = "card_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String, ForeignKey("cards.id"))
    image_url = Column(String, nullable=False)
    image_type = Column(String, nullable=False)  # e.g., 'front', 'back'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships - using string references to avoid circular imports
    card = relationship("Card", back_populates="images")