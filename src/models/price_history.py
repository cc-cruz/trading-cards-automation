from sqlalchemy import Column, String, DateTime, ForeignKey, Float, func
from src.database import Base
import uuid

class CardPriceHistory(Base):
    """Stores historical price points for a card so we can chart value over time."""

    __tablename__ = "card_price_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    price_source = Column(String, nullable=False)
    price = Column(Float, nullable=False) 