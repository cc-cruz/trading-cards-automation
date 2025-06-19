from typing import Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends

from ..database import get_db
from ..utils.price_finder import research_all_prices
from ..models.price_history import CardPriceHistory

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
            pricing_summary = {
                'estimated_value': pricing_data['average_sold_price'],  # alias for backward compatibility
                'average_price': pricing_data['average_sold_price'],
                'listing_price': pricing_data['listing_price'],
                'sample_size': pricing_data['sample_size'],
                'sold_prices': pricing_data['sold_prices'],
                'markup_percent': pricing_data['markup_percent']
            }

            # Optionally persist price history if card_id is provided in card_data
            card_id = card_data.get('id') or card_data.get('card_id')
            if card_id:
                self.add_price_history(card_id, pricing_summary['estimated_value'], price_source="ebay_scrape")

            return pricing_summary

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
        """Return chronological list of price points for a given card."""
        history = (
            self.db.query(CardPriceHistory)
            .filter(CardPriceHistory.card_id == card_id)
            .order_by(CardPriceHistory.timestamp.asc())
            .all()
        )
        return [
            {
                "timestamp": record.timestamp,
                "price": record.price,
                "source": record.price_source,
            }
            for record in history
        ]

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def add_price_history(self, card_id: str, price: float, *, price_source: str) -> None:
        """Persist a new price data point for a card."""
        history_record = CardPriceHistory(
            card_id=card_id,
            price=price,
            price_source=price_source,
        )
        self.db.add(history_record)
        # Flush without committing so caller may decide to commit. But we commit
        # here for simplicity because price history is low-risk.
        self.db.commit()

# Dependency
def get_price_service(db: Session = Depends(get_db)) -> PriceService:
    return PriceService(db) 