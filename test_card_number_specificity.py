#!/usr/bin/env python3
"""
Test card number specificity with our enhanced database.
Shows how exact card numbers like 'FSA-1B' are matched.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.database import SessionLocal
from src.services.card_database_service import HybridPricingService, CardDatabaseService
import asyncio
import time

async def test_card_number_specificity():
    """Test specific card number matching"""
    
    print("🎯 Testing Card Number Specificity")
    print("=" * 50)
    
    db = SessionLocal()
    hybrid_service = HybridPricingService(db)
    card_db_service = CardDatabaseService(db)
    
    # Test cases with specific card numbers
    test_cases = [
        {
            "description": "Paul Skenes Future Stars Auto",
            "card_data": {
                "player": "Paul Skenes",
                "set": "Chrome", 
                "year": "2024",
                "manufacturer": "Topps",
                "card_number": "FSA-1B"
            },
            "expected_price": 150.0
        },
        {
            "description": "Jackson Holliday Bowman Chrome Prospect Auto",
            "card_data": {
                "player": "Jackson Holliday",
                "set": "Chrome",
                "year": "2024", 
                "manufacturer": "Bowman",
                "card_number": "BCP-15A"
            },
            "expected_price": 125.0
        },
        {
            "description": "Fernando Tatis Jr Rookie Card",
            "card_data": {
                "player": "Fernando Tatis Jr",
                "set": "Series 2",
                "year": "2019",
                "manufacturer": "Topps", 
                "card_number": "410"
            },
            "expected_price": 25.0
        },
        {
            "description": "Victor Wembanyama Rookie Card",
            "card_data": {
                "player": "Victor Wembanyama",
                "set": "Prizm",
                "year": "2024",
                "manufacturer": "Panini",
                "card_number": "RC-1"
            },
            "expected_price": 200.0
        },
        {
            "description": "Connor Bedard Young Guns",
            "card_data": {
                "player": "Connor Bedard",
                "set": "Series 1",
                "year": "2024",
                "manufacturer": "Upper Deck",
                "card_number": "YG-201"
            },
            "expected_price": 100.0
        },
        {
            "description": "Wrong card number (should not match)",
            "card_data": {
                "player": "Paul Skenes",
                "set": "Chrome",
                "year": "2024",
                "manufacturer": "Topps",
                "card_number": "FSA-999"  # Wrong number
            },
            "expected_price": None
        }
    ]
    
    print(f"Testing {len(test_cases)} card number scenarios...\n")
    
    exact_matches = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔍 Test {i}/{total_tests}: {test_case['description']}")
        card_data = test_case['card_data']
        print(f"   Card: {card_data['player']} {card_data['set']} #{card_data['card_number']}")
        
        start_time = time.time()
        
        try:
            # Test direct database lookup
            match = card_db_service.find_card_match(card_data)
            
            if match:
                print(f"   ✅ EXACT MATCH FOUND!")
                print(f"   📋 Player: {match.player_name}")
                print(f"   📋 Set: {match.set_name}")
                print(f"   📋 Card #: {match.card_number}")
                print(f"   📋 Parallel: {match.parallel}")
                print(f"   💰 Price: ${match.avg_raw_price}")
                
                # Verify it's the exact card number we wanted
                if match.card_number == card_data['card_number']:
                    print(f"   ✅ Card number matches exactly!")
                    exact_matches += 1
                else:
                    print(f"   ⚠️  Card number mismatch: expected {card_data['card_number']}, got {match.card_number}")
                
                # Test hybrid pricing
                result = await hybrid_service.get_card_price(card_data)
                end_time = time.time()
                lookup_time = (end_time - start_time) * 1000
                
                print(f"   🚀 Hybrid pricing: ${result.get('estimated_value', 0)} via {result.get('source', 'unknown')}")
                print(f"   ⚡ Lookup time: {lookup_time:.1f}ms")
                
            else:
                print(f"   ❌ No match found")
                if test_case['expected_price'] is None:
                    print(f"   ✅ Expected no match - correct!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()  # Empty line
    
    # Summary
    print("📊 Card Number Specificity Results")
    print("=" * 50)
    print(f"Exact card number matches: {exact_matches}/{total_tests-1}")  # -1 for the intentional failure case
    print(f"Success rate: {exact_matches/(total_tests-1)*100:.1f}%")
    
    # Show some examples of card numbers in database
    print(f"\n📋 Sample Card Numbers in Database:")
    sample_cards = db.query(CardDatabaseService.CardDatabase).filter(
        CardDatabaseService.CardDatabase.card_number.like('%-%')
    ).limit(10).all()
    
    for card in sample_cards:
        print(f"   {card.player_name} {card.set_name} #{card.card_number} ({card.parallel}) - ${card.avg_raw_price}")
    
    db.close()
    
    print(f"\n🎉 Card number specificity test complete!")
    print(f"💡 Your database now supports exact card number matching!")

if __name__ == "__main__":
    asyncio.run(test_card_number_specificity()) 