from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, func
from datetime import datetime, timedelta
from fastapi import Depends
import json
import os

from ..database import Base, get_db


class CardDatabase(Base):
    """Local database of known card editions and average market values"""
    __tablename__ = "card_database"
    
    id = Column(String, primary_key=True)
    sport = Column(String, nullable=False)  # MLB, NBA, NFL, NHL
    year = Column(Integer, nullable=False)
    manufacturer = Column(String, nullable=False)  # Topps, Panini, Upper Deck
    set_name = Column(String, nullable=False)  # Prizm, Chrome, Series 1, etc.
    player_name = Column(String, nullable=False)
    card_number = Column(String, nullable=False)
    parallel = Column(String, default="")  # Base, Refractor, /99, etc.
    rookie = Column(String, default=False)
    
    # Market data
    avg_raw_price = Column(Float, default=0.0)
    avg_psa9_price = Column(Float, default=0.0)
    avg_psa10_price = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=func.now())
    sample_size = Column(Integer, default=0)
    
    # Card identification helpers
    search_terms = Column(JSON)  # Alternative names, nicknames, etc.
    card_traits = Column(JSON)   # RC, SP, Auto, etc.


class CardDatabaseService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = {}  # In-memory cache for frequent lookups
        
    def find_card_match(self, card_data: Dict) -> Optional[CardDatabase]:
        """
        Find a match in the local card database for faster pricing.
        Uses fuzzy matching for player names and sets.
        """
        # Extract key search parameters
        player = card_data.get('player', '').strip()
        year = self._extract_year(card_data.get('year'))
        set_name = card_data.get('set', '').strip()
        manufacturer = card_data.get('manufacturer', '').strip()
        card_number = card_data.get('card_number', '').strip()
        
        if not player or not year:
            return None
            
        # Try exact match first
        exact_match = self._exact_match(player, year, set_name, manufacturer, card_number)
        if exact_match:
            return exact_match
            
        # Try fuzzy matching
        fuzzy_match = self._fuzzy_match(player, year, set_name, manufacturer)
        return fuzzy_match
    
    def _exact_match(self, player: str, year: int, set_name: str, 
                    manufacturer: str, card_number: str) -> Optional[CardDatabase]:
        """Attempt exact database match"""
        query = self.db.query(CardDatabase).filter(
            CardDatabase.player_name.ilike(f"%{player}%"),
            CardDatabase.year == year
        )
        
        if set_name:
            query = query.filter(CardDatabase.set_name.ilike(f"%{set_name}%"))
        if manufacturer:
            query = query.filter(CardDatabase.manufacturer.ilike(f"%{manufacturer}%"))
        if card_number:
            query = query.filter(CardDatabase.card_number == card_number)
            
        return query.first()
    
    def _fuzzy_match(self, player: str, year: int, set_name: str, 
                    manufacturer: str) -> Optional[CardDatabase]:
        """Attempt fuzzy matching with broader criteria"""
        # Year range matching (±1 year for sets that span years)
        query = self.db.query(CardDatabase).filter(
            CardDatabase.player_name.ilike(f"%{player}%"),
            CardDatabase.year.between(year - 1, year + 1)
        )
        
        # Manufacturer matching with alternatives
        if manufacturer:
            manufacturer_variants = self._get_manufacturer_variants(manufacturer)
            query = query.filter(CardDatabase.manufacturer.in_(manufacturer_variants))
            
        return query.first()
    
    def _get_manufacturer_variants(self, manufacturer: str) -> List[str]:
        """Get alternative manufacturer names"""
        variants = [manufacturer]
        manufacturer_lower = manufacturer.lower()
        
        if 'topps' in manufacturer_lower:
            variants.extend(['Topps', 'Bowman'])
        elif 'panini' in manufacturer_lower:
            variants.extend(['Panini', 'Donruss', 'Score'])
        elif 'upper' in manufacturer_lower:
            variants.extend(['Upper Deck', 'UD'])
            
        return variants
    
    def _extract_year(self, year_str: str) -> Optional[int]:
        """Extract year from various formats"""
        if isinstance(year_str, int):
            return year_str
        if isinstance(year_str, str) and year_str.isdigit():
            year = int(year_str)
            # Validate reasonable range (last 50 years)
            if 1970 <= year <= datetime.now().year + 1:
                return year
        return None
    
    def get_estimated_price(self, card_data: Dict, condition: str = "raw") -> Optional[float]:
        """
        Get estimated price from local database based on condition.
        Much faster than eBay API calls.
        """
        card_match = self.find_card_match(card_data)
        if not card_match:
            return None
            
        # Get price based on condition
        if condition.lower() == "psa 10":
            return card_match.avg_psa10_price if card_match.avg_psa10_price > 0 else None
        elif condition.lower() == "psa 9":
            return card_match.avg_psa9_price if card_match.avg_psa9_price > 0 else None
        else:  # Raw/ungraded
            return card_match.avg_raw_price if card_match.avg_raw_price > 0 else None
    
    def bulk_populate_database(self, sport: str, years: List[int]):
        """
        Populate database with common cards for a sport and year range.
        This would be run periodically to update the local database.
        """
        # This would connect to card databases, COMC, or other sources
        # to bulk populate common card data
        pass
    
    def update_card_price(self, card_id: str, condition: str, new_price: float, sample_size: int = 1):
        """Update price data for a card in the database"""
        card = self.db.query(CardDatabase).filter(CardDatabase.id == card_id).first()
        if not card:
            return False
            
        # Update based on condition
        if condition.lower() == "psa 10":
            card.avg_psa10_price = new_price
        elif condition.lower() == "psa 9":
            card.avg_psa9_price = new_price
        else:
            card.avg_raw_price = new_price
            
        card.last_updated = datetime.utcnow()
        card.sample_size = sample_size
        
        self.db.commit()
        return True
    
    def get_popular_cards(self, sport: str, year: int, limit: int = 100) -> List[CardDatabase]:
        """Get most popular/valuable cards for a sport and year"""
        return self.db.query(CardDatabase).filter(
            CardDatabase.sport == sport,
            CardDatabase.year == year
        ).order_by(CardDatabase.avg_psa10_price.desc()).limit(limit).all()
    
    def search_cards(self, query: str, sport: str = None, year: int = None) -> List[CardDatabase]:
        """Search cards by player name or set"""
        db_query = self.db.query(CardDatabase).filter(
            CardDatabase.player_name.ilike(f"%{query}%")
        )
        
        if sport:
            db_query = db_query.filter(CardDatabase.sport == sport)
        if year:
            db_query = db_query.filter(CardDatabase.year == year)
            
        return db_query.limit(50).all()


class HybridPricingService:
    """
    Combines local database with eBay API for optimal pricing strategy.
    Uses local DB for common cards, eBay API for rare/unknown cards.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.card_db_service = CardDatabaseService(db)
        
    async def get_card_price(self, card_data: Dict) -> Dict:
        """
        Intelligent pricing that tries local DB first, falls back to eBay API.
        """
        # Try local database first (instant response)
        local_price = self.card_db_service.get_estimated_price(card_data)
        
        if local_price and local_price > 0:
            return {
                'source': 'local_database',
                'estimated_value': local_price,
                'confidence': 'high',
                'last_updated': 'recent',
                'method': 'database_lookup'
            }
        
        # Fall back to eBay API for unknown cards
        from ..utils.price_finder import research_all_prices
        
        try:
            results = research_all_prices([card_data])
            if results and results[0].get('pricing_data'):
                pricing_data = results[0]['pricing_data']
                
                # Cache result in local database for future lookups
                self._cache_price_result(card_data, pricing_data)
                
                return {
                    'source': 'ebay_api',
                    'estimated_value': pricing_data['average_sold_price'],
                    'confidence': 'medium',
                    'sample_size': pricing_data.get('sample_size', 0),
                    'method': 'live_market_data'
                }
        except Exception as e:
            print(f"eBay API failed: {e}")
            
        # Ultimate fallback
        return {
            'source': 'fallback',
            'estimated_value': 1.0,
            'confidence': 'low',
            'method': 'default_estimate'
        }
    
    def _cache_price_result(self, card_data: Dict, pricing_data: Dict):
        """Cache eBay results in local database for future use"""
        # Implementation to save eBay results to local database
        pass


# Dependencies
def get_card_database_service(db: Session = Depends(get_db)) -> CardDatabaseService:
    return CardDatabaseService(db)

def get_hybrid_pricing_service(db: Session = Depends(get_db)) -> HybridPricingService:
    return HybridPricingService(db) 