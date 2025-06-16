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

    async def process_card_image(self, file: UploadFile, collection_id: str, user_id: str) -> dict:
        import os
        import tempfile
        from ..utils.enhanced_card_processor import process_all_images_enhanced
        from ..utils.price_finder import research_all_prices
        
        # Create temporary directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save image to temporary location
        temp_path = f"temp/{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # For now, create a mock card data structure for testing
            # TODO: Replace with actual OCR processing when Google Cloud credentials are set up
            try:
                # Process image using enhanced OCR
                processed_cards = process_all_images_enhanced([temp_path])
                if processed_cards and len(processed_cards) > 0:
                    card_data = processed_cards[0]
                else:
                    # Fallback to mock data if OCR fails
                    card_data = self._create_mock_card_data(file.filename)
            except Exception as ocr_error:
                print(f"OCR processing failed: {ocr_error}")
                # Create mock card data for testing
                card_data = self._create_mock_card_data(file.filename)
            
            # Get price data using existing price research
            # TODO: Enable price research when ready for production
            try:
                cards_with_pricing = research_all_prices([card_data])
                price_data = None
                if cards_with_pricing and len(cards_with_pricing) > 0:
                    pricing_info = cards_with_pricing[0].get('pricing_data')
                    if pricing_info:
                        price_data = {
                            "estimated_value": pricing_info.get('average_sold_price', 0),
                            "listing_price": pricing_info.get('listing_price', 0),
                            "sold_prices": pricing_info.get('sold_prices', []),
                            "sample_size": pricing_info.get('sample_size', 0),
                            "search_query": cards_with_pricing[0].get('search_query', '')
                        }
            except Exception as price_error:
                print(f"Price research failed: {price_error}")
                # Create mock price data for testing
                price_data = {
                    "estimated_value": 10.0,
                    "listing_price": 12.0,
                    "sold_prices": [8.0, 10.0, 12.0],
                    "sample_size": 3,
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }

            # Create card record
            card = Card(
                collection_id=collection_id,
                player_name=card_data.get('player', ''),
                set_name=card_data.get('set', ''),
                year=card_data.get('year', ''),
                card_number=card_data.get('card_number', ''),
                parallel=card_data.get('parallel', ''),
                manufacturer=card_data.get('manufacturer', ''),
                features=card_data.get('features', ''),
                graded=card_data.get('graded', False),
                grade=card_data.get('grade', ''),
                grading_company=card_data.get('grading_company', ''),
                cert_number=card_data.get('cert_number', ''),
                price_data=price_data or {}
            )
            self.db.add(card)
            self.db.commit()
            self.db.refresh(card)

            # For now, store image locally (can be enhanced to upload to cloud storage later)
            # Create permanent storage path
            storage_dir = f"images/cards/{user_id}"
            os.makedirs(storage_dir, exist_ok=True)
            permanent_path = f"{storage_dir}/{card.id}_{file.filename}"
            
            # Move file to permanent location
            import shutil
            shutil.move(temp_path, permanent_path)
            
            # Create image record
            card_image = CardImage(
                card_id=card.id,
                image_url=permanent_path,
                image_type='front'
            )
            self.db.add(card_image)
            self.db.commit()

            return {
                "card_id": card.id,
                "card_data": {
                    "player": card.player_name,
                    "set": card.set_name,
                    "year": card.year,
                    "card_number": card.card_number,
                    "parallel": card.parallel,
                    "manufacturer": card.manufacturer,
                    "features": card.features,
                    "graded": card.graded,
                    "grade": card.grade,
                    "grading_company": card.grading_company,
                    "cert_number": card.cert_number
                },
                "price_data": price_data
            }

        except Exception as e:
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def _create_mock_card_data(self, filename: str) -> dict:
        """Create mock card data for testing when OCR is not available"""
        return {
            "player": "Test Player",
            "set": "Test Set 2023",
            "year": "2023",
            "card_number": "1",
            "parallel": "",
            "manufacturer": "Test Manufacturer",
            "features": "Test Card",
            "graded": False,
            "grade": "",
            "grading_company": "",
            "cert_number": "",
            "filename": filename
        }

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