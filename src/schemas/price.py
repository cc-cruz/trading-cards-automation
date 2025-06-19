from pydantic import BaseModel
from datetime import datetime

class PriceHistoryPoint(BaseModel):
    timestamp: datetime
    price: float
    source: str

    class Config:
        from_attributes = True 