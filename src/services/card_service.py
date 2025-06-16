from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, Depends

from ..database import get_db
from ..models.card import Card, CardImage
from ..models.collection import Collection
from ..schemas.card import CardCreate, CardUpdate
from .price_service import PriceService
from ..utils.card_processor import process_all_images
from ..utils.gcs_url_generator import get_gcs_image_urls
from ..utils.price_finder import research_all_prices

class CardService:
    def __init__(self, db: Session):
        self.db = db
        self.price_service = PriceService(db)

    async def process_card_image(self, file: UploadFile, collection_id: str) -> Card:
        # Save image to temporary location
        temp_path = f"temp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        try:
            # Process image using existing code
            processed_cards = process_all_images([temp_path])
            if not processed_cards:
                raise HTTPException(status_code=400, detail="Failed to process card image")

            card_data = processed_cards[0]
            
            # Get price data
            price_data = await self.price_service.research_price(card_data)

            # Create card record
            card = Card(
                collection_id=collection_id,
                player_name=card_data['player'],
                set_name=card_data['set'],
                year=card_data['year'],
                card_number=card_data['card_number'],
                parallel=card_data['parallel'],
                manufacturer=card_data['manufacturer'],
                features=card_data['features'],
                graded=card_data['graded'],
                grade=card_data['grade'],
                grading_company=card_data['grading_company'],
                cert_number=card_data['cert_number'],
                price_data=price_data
            )
            self.db.add(card)
            self.db.commit()
            self.db.refresh(card)

            # Upload image to GCS and create image record
            image_url = await self.upload_to_gcs(temp_path, card.id)
            card_image = CardImage(
                card_id=card.id,
                image_url=image_url,
                image_type='front'
            )
            self.db.add(card_image)
            self.db.commit()

            return card

        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def upload_to_gcs(self, file_path: str, card_id: str) -> str:
        # Implementation for GCS upload
        # This would use the existing GCS integration code
        pass

    def get_card(self, card_id: str) -> Optional[Card]:
        return self.db.query(Card).filter(Card.id == card_id).first()

    def get_collection_cards(self, collection_id: str) -> List[Card]:
        return self.db.query(Card).filter(Card.collection_id == collection_id).all()

    def update_card(self, card_id: str, card_update: CardUpdate) -> Optional[Card]:
        card = self.get_card(card_id)
        if not card:
            return None

        for field, value in card_update.dict(exclude_unset=True).items():
            setattr(card, field, value)

        self.db.commit()
        self.db.refresh(card)
        return card

    def delete_card(self, card_id: str) -> bool:
        card = self.get_card(card_id)
        if not card:
            return False

        self.db.delete(card)
        self.db.commit()
        return True

# Dependency
def get_card_service(db: Session = Depends(get_db)) -> CardService:
    return CardService(db) 