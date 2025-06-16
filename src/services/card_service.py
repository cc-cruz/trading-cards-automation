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

    def get_user_collection_stats(self, user_id: str) -> dict:
        """Get collection statistics for a user"""
        from sqlalchemy import func
        
        # Get all collections for this user
        collections = self.db.query(Collection).filter(Collection.user_id == user_id).all()
        collection_ids = [c.id for c in collections]
        
        if not collection_ids:
            return {
                "total_cards": 0,
                "total_value": 0,
                "recent_additions": 0
            }
        
        # Total cards count
        total_cards = self.db.query(Card).filter(Card.collection_id.in_(collection_ids)).count()
        
        # Calculate total value (sum of card prices)
        cards_with_prices = self.db.query(Card).filter(
            Card.collection_id.in_(collection_ids),
            Card.price_data.isnot(None)
        ).all()
        
        total_value = 0
        for card in cards_with_prices:
            if card.price_data and isinstance(card.price_data, dict):
                # Extract price from price_data structure
                price = card.price_data.get('estimated_value', 0)
                if isinstance(price, (int, float)):
                    total_value += price
        
        # Recent additions (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_additions = self.db.query(Card).filter(
            Card.collection_id.in_(collection_ids),
            Card.created_at >= thirty_days_ago
        ).count()
        
        return {
            "total_cards": total_cards,
            "total_value": round(total_value, 2),
            "recent_additions": recent_additions
        }

    def get_recent_cards(self, user_id: str, limit: int = 6) -> List[dict]:
        """Get recently added cards for a user"""
        from sqlalchemy import desc
        
        # Get all collections for this user
        collections = self.db.query(Collection).filter(Collection.user_id == user_id).all()
        collection_ids = [c.id for c in collections]
        
        if not collection_ids:
            return []
        
        # Get recent cards with their images
        recent_cards = self.db.query(Card).filter(
            Card.collection_id.in_(collection_ids)
        ).order_by(desc(Card.created_at)).limit(limit).all()
        
        result = []
        for card in recent_cards:
            # Get the first image for this card
            card_image = self.db.query(CardImage).filter(CardImage.card_id == card.id).first()
            
            # Extract price from price_data
            price = 0
            if card.price_data and isinstance(card.price_data, dict):
                price = card.price_data.get('estimated_value', 0)
            
            result.append({
                "id": card.id,
                "name": f"{card.player_name} {card.year}" if card.player_name else "Unknown Card",
                "set": card.set_name or "Unknown Set",
                "condition": f"Grade {card.grade}" if card.grade else card.parallel or "Raw",
                "price": price,
                "image_url": card_image.image_url if card_image else "/images/card-placeholder.jpg"
            })
        
        return result

# Dependency
def get_card_service(db: Session = Depends(get_db)) -> CardService:
    return CardService(db) 