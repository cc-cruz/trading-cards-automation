from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class CardBase(BaseModel):
    player_name: Optional[str] = None
    set_name: Optional[str] = None
    year: Optional[str] = None
    card_number: Optional[str] = None
    parallel: Optional[str] = None
    manufacturer: Optional[str] = None
    features: Optional[Dict] = None
    graded: Optional[str] = None
    grade: Optional[str] = None
    grading_company: Optional[str] = None
    cert_number: Optional[str] = None

class CardCreate(CardBase):
    collection_id: str
    image: str  # Base64 encoded image

class CardUpdate(CardBase):
    pass

class CardImage(BaseModel):
    id: str
    image_url: str
    image_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Card(CardBase):
    id: str
    collection_id: str
    price_data: Optional[Dict] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    images: List[CardImage] = []

    class Config:
        from_attributes = True 