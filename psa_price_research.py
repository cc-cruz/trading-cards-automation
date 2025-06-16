#!/usr/bin/env python3

import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import json
from datetime import datetime
import pandas as pd

def get_psa_card_definitions():
    """
    Define the 4 PSA graded cards with multiple search variations for better pricing.
    """
    return [
        {
            'name': 'Juan Soto PSA 9 Aqua Equinox Refractor',
            'player': 'Juan Soto',
            'grade': '9',
            'year': '2024',
            'set': 'Topps Chrome Cosmic',
            'parallel': 'Aqua Equinox Refractor',
            'card_number': '42',
            'search_variations': [
                'Juan Soto 2024 Topps Chrome Cosmic Aqua Equinox Refractor PSA 9',
                'Juan Soto 2024 Chrome Cosmic Aqua Equinox PSA 9',
                'Juan Soto 2024 Topps Chrome Aqua Equinox Refractor PSA 9',
                'Juan Soto PSA 9 Aqua Equinox 2024',
                'Juan Soto Chrome Cosmic PSA 9 Refractor'
            ]
        },
        {
            'name': 'Fernando Tatis Jr PSA 10 Rookie',
            'player': 'Fernando Tatis Jr',
            'grade': '10',
            'year': '2019',
            'set': 'Topps',
            'parallel': 'Rookie Card',
            'card_number': '410',
            'search_variations': [
                'Fernando Tatis Jr 2019 Topps 410 PSA 10 Rookie',
                'Fernando Tatis Jr 2019 Topps RC PSA 10',
                'Fernando Tatis Jr PSA 10 Rookie Card 2019',
                'Tatis Jr 2019 Topps 410 PSA 10',
                'Fernando Tatis 2019 Topps Series 2 PSA 10'
            ]
        },
        {
            'name': 'Chourio Salas International Impact PSA 10',
            'player': 'Chourio Salas',
            'grade': '10',
            'year': '2024',
            'set': 'Topps Chrome',
            'parallel': 'International Impact',
            'card_number': 'II-CS',
            'search_variations': [
                'Chourio Salas 2024 Topps Chrome International Impact PSA 10',
                'Chourio Salas International Impact PSA 10',
                'Chourio Salas 2024 Chrome PSA 10',
                'Chourio Salas PSA 10 International',
                'Salas Chourio International Impact PSA 10'
            ]
        },
        {
            'name': 'Jackson Merrill Chrome Cosmic PSA 10',
            'player': 'Jackson Merrill',
            'grade': '10',
            'year': '2024',
            'set': 'Topps Chrome Cosmic',
            'parallel': 'Chrome Cosmic',
            'card_number': '194',
            'search_variations': [
                'Jackson Merrill 2024 Topps Chrome Cosmic PSA 10',
                'Jackson Merrill Chrome Cosmic PSA 10',
                'Jackson Merrill 2024 Chrome Cosmic PSA 10',
                'Jackson Merrill PSA 10 Chrome Cosmic',
                'Jackson Merrill Topps Chrome Cosmic PSA 10'
            ]
        }
    ]

def scrape_ebay_sold_listings_enhanced(search_query, max_results=10):
    """Enhanced eBay scraping with better error handling and more data extraction."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # eBay sold listings URL with additional filters
    encoded_query = quote_plus(search_query)
    url = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={encoded_query}&_sacat=261328&LH_Sold=1&LH_Complete=1&_sop=13&LH_ItemCondition=3000"
    
    print(f"  🔍 Searching: {search_query}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find sold listing items with multiple selectors
        items = soup.find_all('div', class_='s-item__wrapper clearfix')
        if not items:
            items = soup.find_all('div', class_='s-item')
        
        prices = []
        listings_data = []
        
        for item in items[:max_results]:
            try:
                # Extract price
                price_elem = item.find('span', class_='s-item__price')
                if not price_elem:
                    price_elem = item.find('span', class_='notranslate')
                
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Extract numeric price
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(',', ''))
                            
                            # Extract title for verification
                            title_elem = item.find('h3', class_='s-item__title')
                            title = title_elem.get_text(strip=True) if title_elem else 'No title'
                            
                            # Extract sold date
                            date_elem = item.find('span', class_='s-item__endedDate')
                            sold_date = date_elem.get_text(strip=True) if date_elem else 'Unknown date'
                            
                            prices.append(price)
                            listings_data.append({
                                'price': price,
                                'title': title,
                                'sold_date': sold_date,
                                'search_query': search_query
                            })
                        except ValueError:
                            continue
            except Exception as e:
                continue
        
        return prices, listings_data
    
    except requests.exceptions.RequestException as e:
        print(f"    ❌ Request error: {e}")
        return [], []
    except Exception as e:
        print(f"    ❌ Parsing error: {e}")
        return [], []

def research_psa_card_prices(card_data):
    """Research prices for a single PSA card using multiple search variations."""
    print(f"\n🏆 Researching: {card_data['name']}")
    print("-" * 50)
    
    all_prices = []
    all_listings = []
    successful_searches = 0
    
    for i, search_query in enumerate(card_data['search_variations'], 1):
        print(f"  Search {i}/{len(card_data['search_variations'])}")
        
        try:
            prices, listings = scrape_ebay_sold_listings_enhanced(search_query, max_results=8)
            
            if prices:
                all_prices.extend(prices)
                all_listings.extend(listings)
                successful_searches += 1
                print(f"    ✅ Found {len(prices)} sold listings")
                print(f"    💰 Price range: ${min(prices):.2f} - ${max(prices):.2f}")
            else:
                print(f"    ❌ No listings found")
            
            # Rate limiting
            time.sleep(3)
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            time.sleep(2)
    
    # Analyze results
    if all_prices:
        # Remove extreme outliers (more than 3 standard deviations)
        if len(all_prices) > 3:
            mean_price = sum(all_prices) / len(all_prices)
            std_dev = (sum((x - mean_price) ** 2 for x in all_prices) / len(all_prices)) ** 0.5
            filtered_prices = [p for p in all_prices if abs(p - mean_price) <= 3 * std_dev]
            if len(filtered_prices) >= len(all_prices) * 0.7:  # Keep if we retain 70% of data
                all_prices = filtered_prices
        
        # Calculate statistics
        avg_price = sum(all_prices) / len(all_prices)
        min_price = min(all_prices)
        max_price = max(all_prices)
        median_price = sorted(all_prices)[len(all_prices) // 2]
        
        # Determine listing price with conservative markup
        listing_price = avg_price * 1.15  # 15% markup
        
        results = {
            'card_name': card_data['name'],
            'player': card_data['player'],
            'grade': card_data['grade'],
            'total_listings_found': len(all_prices),
            'successful_searches': successful_searches,
            'average_sold_price': round(avg_price, 2),
            'median_sold_price': round(median_price, 2),
            'min_sold_price': round(min_price, 2),
            'max_sold_price': round(max_price, 2),
            'recommended_listing_price': round(listing_price, 2),
            'price_range': f"${min_price:.2f} - ${max_price:.2f}",
            'all_prices': all_prices,
            'sample_listings': all_listings[:5]  # Keep top 5 for reference
        }
        
        print(f"\n📊 Results Summary:")
        print(f"    Total sold listings: {len(all_prices)}")
        print(f"    Average price: ${avg_price:.2f}")
        print(f"    Median price: ${median_price:.2f}")
        print(f"    Price range: ${min_price:.2f} - ${max_price:.2f}")
        print(f"    Recommended listing: ${listing_price:.2f}")
        
        return results
    else:
        print(f"    ❌ No pricing data found across all searches")
        return {
            'card_name': card_data['name'],
            'player': card_data['player'],
            'grade': card_data['grade'],
            'total_listings_found': 0,
            'successful_searches': 0,
            'error': 'No sold listings found'
        }

def export_pricing_results(all_results):
    """Export comprehensive pricing results to CSV and JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create summary CSV
    csv_data = []
    for result in all_results:
        if 'average_sold_price' in result:
            csv_data.append({
                'Card': result['card_name'],
                'Player': result['player'],
                'PSA_Grade': result['grade'],
                'Listings_Found': result['total_listings_found'],
                'Average_Price': f"${result['average_sold_price']:.2f}",
                'Median_Price': f"${result['median_sold_price']:.2f}",
                'Price_Range': result['price_range'],
                'Recommended_Listing': f"${result['recommended_listing_price']:.2f}",
                'Market_Confidence': 'High' if result['total_listings_found'] >= 10 else 'Medium' if result['total_listings_found'] >= 5 else 'Low'
            })
        else:
            csv_data.append({
                'Card': result['card_name'],
                'Player': result['player'],
                'PSA_Grade': result['grade'],
                'Listings_Found': 0,
                'Average_Price': 'No data',
                'Median_Price': 'No data',
                'Price_Range': 'No data',
                'Recommended_Listing': 'No data',
                'Market_Confidence': 'None'
            })
    
    # Export CSV
    df = pd.DataFrame(csv_data)
    csv_filename = f"psa_price_research_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    
    # Export detailed JSON
    json_filename = f"psa_price_research_detailed_{timestamp}.json"
    with open(json_filename, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📁 Files exported:")
    print(f"  📊 Summary CSV: {csv_filename}")
    print(f"  📋 Detailed JSON: {json_filename}")
    
    return csv_filename, json_filename

def main():
    """Main function to research prices for all 4 PSA graded cards."""
    print("=== Comprehensive PSA Card Price Research ===")
    print("🎯 Researching recent sold prices for 4 PSA graded cards")
    print("=" * 60)
    
    cards = get_psa_card_definitions()
    all_results = []
    
    for i, card in enumerate(cards, 1):
        print(f"\n🔄 Card {i}/4: Starting research...")
        result = research_psa_card_prices(card)
        all_results.append(result)
        
        # Longer pause between cards to avoid rate limiting
        if i < len(cards):
            print(f"\n⏳ Waiting 10 seconds before next card...")
            time.sleep(10)
    
    # Export results
    print(f"\n🔄 Exporting comprehensive results...")
    csv_file, json_file = export_pricing_results(all_results)
    
    # Final summary
    print(f"\n🎉 Comprehensive Price Research Complete!")
    print("=" * 60)
    
    successful_cards = [r for r in all_results if 'average_sold_price' in r]
    total_listings = sum(r.get('total_listings_found', 0) for r in all_results)
    
    print(f"📊 Research Summary:")
    print(f"  Cards researched: {len(cards)}")
    print(f"  Cards with pricing data: {len(successful_cards)}")
    print(f"  Total sold listings analyzed: {total_listings}")
    
    if successful_cards:
        print(f"\n💰 Pricing Summary:")
        for result in successful_cards:
            print(f"  🏆 {result['player']} PSA {result['grade']}: ${result['average_sold_price']:.2f} avg (${result['recommended_listing_price']:.2f} recommended)")
    
    print(f"\n📁 Detailed results saved to:")
    print(f"  {csv_file}")
    print(f"  {json_file}")

if __name__ == '__main__':
    main() 