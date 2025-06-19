from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from fastapi import Depends

from ..models.user import User
from ..models.collection import Collection
from ..models.card import Card
from ..models.price_history import CardPriceHistory
from ..database import get_db


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a user's collection"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Get basic stats
        total_cards = 0
        total_value = 0.0
        recent_additions = 0
        collections_stats = []

        # 30 days ago for recent additions
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        for collection in user.collections:
            collection_cards = collection.cards.all()
            collection_value = 0.0
            
            for card in collection_cards:
                total_cards += 1
                if card.price_data and isinstance(card.price_data, dict):
                    card_value = card.price_data.get('estimated_value', 0)
                    if isinstance(card_value, (int, float)):
                        collection_value += card_value
                        total_value += card_value

            # Count recent additions for this collection
            recent_count = collection.cards.filter(Card.created_at >= thirty_days_ago).count()
            recent_additions += recent_count

            # Collection stats
            avg_value = collection_value / len(collection_cards) if collection_cards else 0
            collections_stats.append({
                'id': collection.id,
                'name': collection.name,
                'card_count': len(collection_cards),
                'total_value': collection_value,
                'avg_value': avg_value
            })

        # Get top valuable cards
        top_cards = self._get_top_valuable_cards(user_id, limit=5)

        # Get value trends (placeholder for now)
        value_trends = self._get_value_trends(user_id)

        return {
            'total_cards': total_cards,
            'total_value': total_value,
            'recent_additions': recent_additions,
            'collections': collections_stats,
            'top_cards': top_cards,
            'value_trends': value_trends
        }

    def _get_top_valuable_cards(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the top valuable cards for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        all_cards = []
        for collection in user.collections:
            for card in collection.cards:
                if card.price_data and isinstance(card.price_data, dict):
                    value = card.price_data.get('estimated_value', 0)
                    if isinstance(value, (int, float)) and value > 0:
                        # Get first image
                        first_image = card.images.first()
                        image_url = first_image.image_url if first_image else '/images/card-placeholder.jpg'
                        
                        all_cards.append({
                            'id': card.id,
                            'name': f"{card.player_name} {card.year}" if card.player_name else "Unknown Card",
                            'set': card.set_name or "Unknown Set",
                            'condition': f"Grade {card.grade}" if card.grade else card.parallel or "Raw",
                            'value': value,
                            'image_url': image_url
                        })

        # Sort by value and return top cards
        all_cards.sort(key=lambda x: x['value'], reverse=True)
        return all_cards[:limit]

    def _get_value_trends(self, user_id: str) -> List[Dict[str, Any]]:
        """Return daily total portfolio value over the last 90 days."""
        # Get all card IDs for user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        card_ids = [card.id for collection in user.collections for card in collection.cards]
        if not card_ids:
            return []

        # Pull history within window
        window_start = datetime.utcnow() - timedelta(days=90)

        history_rows = (
            self.db.query(CardPriceHistory)
            .filter(CardPriceHistory.card_id.in_(card_ids))
            .filter(CardPriceHistory.timestamp >= window_start)
            .all()
        )

        # Bucket by date
        daily_totals: Dict[str, float] = {}
        for row in history_rows:
            date_key = row.timestamp.strftime("%Y-%m-%d")
            daily_totals[date_key] = daily_totals.get(date_key, 0) + row.price

        # Return sorted list
        trend = [
            {"date": day, "total_value": daily_totals[day]} for day in sorted(daily_totals.keys())
        ]
        return trend

    def get_collection_analytics(self, collection_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific collection"""
        collection = self.db.query(Collection).filter(
            Collection.id == collection_id,
            Collection.user_id == user_id
        ).first()
        
        if not collection:
            return {}

        cards = collection.cards.all()
        total_value = 0.0
        graded_count = 0
        manufacturer_stats = {}
        year_stats = {}
        
        for card in cards:
            # Value calculation
            if card.price_data and isinstance(card.price_data, dict):
                value = card.price_data.get('estimated_value', 0)
                if isinstance(value, (int, float)):
                    total_value += value

            # Graded count
            if card.graded and card.grade:
                graded_count += 1

            # Manufacturer stats
            manufacturer = card.manufacturer or 'Unknown'
            manufacturer_stats[manufacturer] = manufacturer_stats.get(manufacturer, 0) + 1

            # Year stats
            year = card.year or 'Unknown'
            year_stats[year] = year_stats.get(year, 0) + 1

        avg_value = total_value / len(cards) if cards else 0
        graded_percentage = (graded_count / len(cards) * 100) if cards else 0

        return {
            'collection_id': collection.id,
            'name': collection.name,
            'description': collection.description,
            'total_cards': len(cards),
            'total_value': total_value,
            'avg_value': avg_value,
            'graded_count': graded_count,
            'graded_percentage': graded_percentage,
            'manufacturer_breakdown': manufacturer_stats,
            'year_breakdown': year_stats,
            'recent_additions': collection.cards.filter(
                Card.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
        }

    def get_market_insights(self, user_id: str) -> Dict[str, Any]:
        """Get market insights and trends"""
        # This would analyze market trends, hot cards, etc.
        # Placeholder for now
        return {
            'trending_players': [],
            'hot_sets': [],
            'market_opportunities': [],
            'price_alerts': []
        }


# Dependency
def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db) 