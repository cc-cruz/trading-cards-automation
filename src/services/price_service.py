from typing import Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends

from ..database import get_db
from ..utils.price_finder import research_all_prices

class PriceService:
    def __init__(self, db: Session):
        self.db = db

    async def research_price(self, card_data: Dict) -> Optional[Dict]:
        """
        Research price for a single card using existing price finder code.
        """
        try:
            # Convert single card to list format expected by research_all_prices
            cards = [card_data]
            results = research_all_prices(cards)
            
            if not results or not results[0].get('pricing_data'):
                return None

            pricing_data = results[0]['pricing_data']
            return {
                'average_price': pricing_data['average_sold_price'],
                'listing_price': pricing_data['listing_price'],
                'sample_size': pricing_data['sample_size'],
                'sold_prices': pricing_data['sold_prices'],
                'markup_percent': pricing_data['markup_percent']
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error researching price: {str(e)}"
            )

    async def research_bulk_prices(self, cards_data: list) -> list:
        """
        Research prices for multiple cards in bulk.
        """
        try:
            results = research_all_prices(cards_data)
            return [
                {
                    'card_id': card.get('id'),
                    'pricing_data': card.get('pricing_data'),
                    'error': card.get('pricing_error')
                }
                for card in results
            ]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error researching bulk prices: {str(e)}"
            )

    def get_price_history(self, card_id: str) -> Optional[list]:
        """
        Get price history for a specific card.
        This would be implemented when we add price history tracking.
        """
        # TODO: Implement price history tracking
        return None

# Dependency
def get_price_service(db: Session = Depends(get_db)) -> PriceService:
    return PriceService(db) 