from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, Depends
import uuid

from src.database import get_db
from src.models.card import Card, CardImage
from src.models.collection import Collection
from src.schemas.card import CardCreate, CardUpdate
from .price_service import PriceService
from .card_database_service import HybridPricingService, get_hybrid_pricing_service
from src.utils.card_processor import process_all_images
from src.utils.gcs_url_generator import get_gcs_image_urls
from src.utils.price_finder import research_all_prices

class CardService:
    def __init__(self, db: Session):
        self.db = db
        self.price_service = PriceService(db)
        self.hybrid_pricing_service = HybridPricingService(db)

    async def process_card_image(self, file: UploadFile, collection_id: str, user_id: str) -> dict:
        import os
        import tempfile
        from src.utils.enhanced_card_processor import process_all_images_enhanced
        
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
            
            # Process image using enhanced OCR
            processed_cards = process_all_images_enhanced([temp_path])
            if processed_cards and len(processed_cards) > 0:
                card_data = processed_cards[0]
            else:
                # If OCR returns no results, create basic card structure
                card_data = {
                    "player": "Unknown Player",
                    "set": "Unknown Set",
                    "year": "Unknown",
                    "card_number": "",
                    "parallel": "",
                    "manufacturer": "Unknown",
                    "features": "",
                    "graded": False,
                    "grade": "",
                    "grading_company": "",
                    "cert_number": "",
                    "filename": file.filename
                }
            
            # 🚀 NEW: Use hybrid pricing (local DB + eBay fallback)
            print(f"🔍 Getting price for: {card_data.get('player')} {card_data.get('set')} {card_data.get('year')}")
            
            try:
                hybrid_pricing_result = await self.hybrid_pricing_service.get_card_price(card_data)
                
                price_data = {
                    "estimated_value": hybrid_pricing_result.get('estimated_value', 0.0),
                    "listing_price": hybrid_pricing_result.get('estimated_value', 0.0) * 1.15,  # 15% markup
                    "confidence": hybrid_pricing_result.get('confidence', 'unknown'),
                    "source": hybrid_pricing_result.get('source', 'unknown'),
                    "method": hybrid_pricing_result.get('method', 'unknown'),
                    "sample_size": hybrid_pricing_result.get('sample_size', 0),
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }
                
                print(f"✅ Price found via {hybrid_pricing_result.get('source')}: ${hybrid_pricing_result.get('estimated_value', 0)}")
                
            except Exception as pricing_error:
                print(f"❌ Hybrid pricing failed: {pricing_error}")
                # Ultimate fallback
                price_data = {
                    "estimated_value": 1.0,
                    "listing_price": 1.15,
                    "confidence": "low",
                    "source": "fallback",
                    "method": "default",
                    "sample_size": 0,
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

            # Persist the initial price point to history
            if price_data and isinstance(price_data, dict):
                estimated_value = price_data.get("estimated_value") or price_data.get("average_price")
                if isinstance(estimated_value, (int, float)):
                    # Use source field if provided; fallback to price_data['source']
                    price_source = price_data.get("source", "unknown")
                    try:
                        self.price_service.add_price_history(card.id, float(estimated_value), price_source=price_source)
                    except Exception as history_err:
                        # Log but don't fail the main flow
                        print(f"⚠️  Failed to record price history: {history_err}")

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
        from src.models.user import User
        
        # Get user with collections using relationship
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "total_cards": 0,
                "total_value": 0,
                "recent_additions": 0
            }
        
        # Use relationship to get collections
        collections = user.collections.all()
        
        if not collections:
            return {
                "total_cards": 0,
                "total_value": 0,
                "recent_additions": 0
            }
        
        # Calculate stats using relationships
        total_cards = 0
        total_value = 0
        
        for collection in collections:
            collection_cards = collection.cards.all()
            total_cards += len(collection_cards)
            
            # Calculate value for cards in this collection
            for card in collection_cards:
                if card.price_data and isinstance(card.price_data, dict):
                    price = card.price_data.get('estimated_value', 0)
                    if isinstance(price, (int, float)):
                        total_value += price
        
        # Recent additions (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_additions = 0
        for collection in collections:
            recent_count = collection.cards.filter(Card.created_at >= thirty_days_ago).count()
            recent_additions += recent_count
        
        return {
            "total_cards": total_cards,
            "total_value": round(total_value, 2),
            "recent_additions": recent_additions
        }

    def get_recent_cards(self, user_id: str, limit: int = 6) -> List[dict]:
        """Get recently added cards for a user"""
        from sqlalchemy import desc
        from src.models.user import User
        
        # Get user with collections using relationship
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Get all cards from user's collections using relationships
        all_cards = []
        for collection in user.collections:
            collection_cards = collection.cards.order_by(desc(Card.created_at)).all()
            all_cards.extend(collection_cards)
        
        # Sort all cards by creation date and limit
        all_cards.sort(key=lambda x: x.created_at, reverse=True)
        recent_cards = all_cards[:limit]
        
        result = []
        for card in recent_cards:
            # Use relationship to get first image
            first_image = card.images.first()
            
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
                "image_url": first_image.image_url if first_image else "/images/card-placeholder.jpg"
            })
        
        return result

# Dependency
def get_card_service(db: Session = Depends(get_db)) -> CardService:
    return CardService(db) 