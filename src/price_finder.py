import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from tqdm import tqdm
import re

def _build_search_query(card):
    """Build eBay search query from card data."""
    query_parts = []
    
    if card.get('player'):
        query_parts.append(card['player'])
    if card.get('set'):
        query_parts.append(card['set'])
    if card.get('year'):
        query_parts.append(str(card['year']))
    if card.get('card_number'):
        query_parts.append(f"#{card['card_number']}")
    
    query_parts.append("sold")
    return " ".join(query_parts)

def _scrape_ebay_sold_listings(search_query, max_results=5):
    """Scrape eBay sold listings for a given search query."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # eBay sold listings URL
    encoded_query = quote_plus(search_query)
    url = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={encoded_query}&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=13"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find sold listing items
        items = soup.find_all('div', class_='s-item__wrapper clearfix')
        
        prices = []
        for item in items[:max_results]:
            # Extract price
            price_elem = item.find('span', class_='s-item__price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numeric price
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(',', ''))
                        prices.append(price)
                    except ValueError:
                        continue
        
        return prices
    
    except Exception as e:
        print(f"Error scraping eBay for '{search_query}': {e}")
        return []

def _calculate_listing_price(sold_prices, markup_percent=18):
    """Calculate listing price from sold prices with markup."""
    if not sold_prices:
        return None
    
    # Remove outliers (prices more than 2 standard deviations from mean)
    if len(sold_prices) > 2:
        mean_price = sum(sold_prices) / len(sold_prices)
        std_dev = (sum((x - mean_price) ** 2 for x in sold_prices) / len(sold_prices)) ** 0.5
        filtered_prices = [p for p in sold_prices if abs(p - mean_price) <= 2 * std_dev]
        if filtered_prices:
            sold_prices = filtered_prices
    
    average_price = sum(sold_prices) / len(sold_prices)
    listing_price = average_price * (1 + markup_percent / 100)
    
    return {
        'sold_prices': sold_prices,
        'average_sold_price': round(average_price, 2),
        'listing_price': round(listing_price, 2),
        'markup_percent': markup_percent,
        'sample_size': len(sold_prices)
    }

def research_all_prices(cards):
    """
    Scrapes eBay sold listings to find average prices for a list of cards.
    - Only processes cards with both player name AND set/edition
    - Constructs a search query for each card.
    - Scrapes the last 5 sold listings from the last 90 days.
    - Calculates the average price.
    - Adds an 18% markup to determine the listing price.
    - Includes rate limiting to avoid being blocked.
    - Returns the list of cards with pricing information added.
    """
    print("Step 3: Researching prices on eBay...")
    
    if not cards:
        print("No cards provided for price research.")
        return []
    
    # Filter cards to only include those with both player AND set
    valid_cards = []
    skipped_cards = []
    
    for card in cards:
        player = card.get('player', '').strip()
        card_set = card.get('set', '').strip()
        
        # Check if we have both player name and set/edition
        if player and card_set and len(player) > 2 and len(card_set) > 2:
            # Additional validation - check if player looks like a real name
            if ' ' in player or player.count(' ') >= 1:  # Real names usually have spaces
                valid_cards.append(card)
            else:
                skipped_cards.append(card)
        else:
            skipped_cards.append(card)
    
    print(f"Found {len(valid_cards)} cards with both player name and set/edition")
    print(f"Skipping {len(skipped_cards)} cards with incomplete data")
    
    priced_cards = []
    
    for card in tqdm(valid_cards, desc="Researching prices"):
        search_query = _build_search_query(card)
        
        if not search_query or search_query == "sold":
            # Skip cards with insufficient data
            card_with_price = card.copy()
            card_with_price.update({
                'search_query': search_query,
                'pricing_data': None,
                'pricing_error': 'Insufficient card data for search'
            })
            priced_cards.append(card_with_price)
            continue
        
        try:
            sold_prices = _scrape_ebay_sold_listings(search_query)
            pricing_data = _calculate_listing_price(sold_prices)
            
            card_with_price = card.copy()
            card_with_price.update({
                'search_query': search_query,
                'pricing_data': pricing_data,
                'pricing_error': None if pricing_data else 'No sold listings found'
            })
            priced_cards.append(card_with_price)
            
        except Exception as e:
            card_with_price = card.copy()
            card_with_price.update({
                'search_query': search_query,
                'pricing_data': None,
                'pricing_error': str(e)
            })
            priced_cards.append(card_with_price)
        
        # Rate limiting to avoid being blocked
        time.sleep(2)
    
    # Add skipped cards to the result without pricing data
    for card in skipped_cards:
        card_with_price = card.copy()
        card_with_price.update({
            'search_query': 'Skipped - insufficient data',
            'pricing_data': None,
            'pricing_error': 'Missing player name or set/edition'
        })
        priced_cards.append(card_with_price)
    
    print("Price research complete.")
    print(f"Processed {len(valid_cards)} cards for pricing")
    print(f"Skipped {len(skipped_cards)} cards due to incomplete data")
    return priced_cards

if __name__ == '__main__':
    # Test with sample card data
    test_cards = [
        {
            'player': 'Michael Jordan',
            'set': 'Topps',
            'year': '1986',
            'card_number': '57'
        },
        {
            'player': 'LeBron James',
            'set': 'Topps Chrome',
            'year': '2003',
            'card_number': '111'
        }
    ]
    
    results = research_all_prices(test_cards)
    print("\n--- Pricing Results ---")
    for card in results:
        print(f"Query: {card['search_query']}")
        if card['pricing_data']:
            print(f"  Average Sold: ${card['pricing_data']['average_sold_price']}")
            print(f"  Listing Price: ${card['pricing_data']['listing_price']}")
            print(f"  Sample Size: {card['pricing_data']['sample_size']}")
        else:
            print(f"  Error: {card['pricing_error']}")
        print("-" * 10) 