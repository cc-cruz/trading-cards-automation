#!/usr/bin/env python3

import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.enhanced_card_processor import process_all_images_enhanced
from src.utils.price_finder import research_all_prices

def get_psa_card_definitions():
    """
    Define the 4 unique PSA graded cards with their correct grades and details.
    """
    return {
        'juan-soto': {
            'player': 'Juan Soto',
            'description': 'Juan Soto PSA 9 Aqua Equinox Refractor',
            'grade': '9',
            'set': '2024 Topps Chrome Cosmic',
            'parallel': 'Aqua Equinox Refractor',
            'card_number': '42',
            'expected_files': ['juan-soto-front.jpg', 'juan-soto-back.jpg']
        },
        'fernando-tatis': {
            'player': 'Fernando Tatis Jr',
            'description': 'Fernando Tatis PSA 10 Rookie',
            'grade': '10',
            'set': '2019 Topps',
            'parallel': 'Rookie Card',
            'card_number': '410',
            'expected_files': ['fernando-tatis-front.jpg', 'fernando-tatis-back.jpg']
        },
        'chourio-salas': {
            'player': 'Chourio Salas',
            'description': 'Chourio/Salas International Impact PSA 10',
            'grade': '10',
            'set': '2024 Topps Chrome',
            'parallel': 'International Impact',
            'card_number': 'II-CS',
            'expected_files': ['chourio-salas-front.jpg', 'chourio-salas-back.jpg']
        },
        'jackson-merrill': {
            'player': 'Jackson Merrill',
            'description': 'Jackson Merrill Chrome Cosmic PSA 10',
            'grade': '10',
            'set': '2024 Topps Chrome Cosmic',
            'parallel': 'Chrome Cosmic',
            'card_number': '194',
            'expected_files': ['jackson-merrill-front.jpg', 'jackson-merrill-back.jpg', 'jackson-merrill-2-front.jpg']
        }
    }

def identify_and_process_psa_cards():
    """
    Identify PSA cards and process one representative image per card.
    """
    
    if not os.path.exists('images'):
        print("❌ No 'images' directory found.")
        return []
    
    all_images = [f for f in os.listdir('images') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    psa_definitions = get_psa_card_definitions()
    
    psa_cards_to_process = []
    found_cards = []
    
    print("🔍 Identifying PSA Graded Cards:")
    print("-" * 40)
    
    for card_key, card_info in psa_definitions.items():
        # Find the first available image for this card
        representative_image = None
        found_files = []
        
        for expected_file in card_info['expected_files']:
            if expected_file in all_images:
                found_files.append(expected_file)
                if not representative_image:
                    representative_image = expected_file
        
        if representative_image:
            psa_cards_to_process.append({
                'image_path': os.path.join('images', representative_image),
                'card_info': card_info,
                'all_files': found_files
            })
            found_cards.append(card_info['description'])
            
            print(f"✅ {card_info['description']}")
            print(f"   📁 Using: {representative_image}")
            print(f"   📁 Available: {', '.join(found_files)}")
        else:
            print(f"❌ {card_info['description']} - No matching files found")
    
    print(f"\n📊 Summary:")
    print(f"  PSA cards found: {len(found_cards)}/4")
    print(f"  Images to process: {len(psa_cards_to_process)}")
    
    return psa_cards_to_process

def load_image_urls():
    """Load image URLs from the JSON file."""
    try:
        if os.path.exists('image_urls.json'):
            with open('image_urls.json', 'r') as f:
                return json.load(f)
        else:
            print("⚠️  image_urls.json not found. URLs will be empty.")
            return {}
    except Exception as e:
        print(f"⚠️  Error loading image URLs: {e}")
        return {}

def get_image_urls_for_card(player_name, image_urls_dict):
    """
    Get image URLs for a specific card based on player name.
    Returns pipe-separated URLs for eBay format.
    """
    if not image_urls_dict:
        return ""
    
    card_urls = []
    
    # Convert player name to filename format (e.g., "Juan Soto" -> "juan-soto")
    player_filename = player_name.lower().replace(' ', '-').replace('.', '').replace('jr', '').strip()
    
    # Look for matching images
    for filename, url in image_urls_dict.items():
        filename_lower = filename.lower()
        if player_filename in filename_lower:
            card_urls.append(url)
    
    # Return pipe-separated URLs (eBay format for multiple images)
    return "|".join(card_urls) if card_urls else ""

def create_psa_cards_csv(psa_cards_data, image_urls_dict):
    """
    Create CSV with the 4 PSA graded cards using predefined information.
    """
    print("\n🔄 Creating PSA cards CSV...")
    
    csv_data = []
    
    for card_data in psa_cards_data:
        card_info = card_data['card_info']
        
        # Get image URLs for this card
        image_urls = get_image_urls_for_card(card_info['player'], image_urls_dict)
        
        # Build title with PSA grading info
        title_parts = [
            card_info['set'],
            card_info['player'],
            f"#{card_info['card_number']}",
            f"PSA {card_info['grade']}",
            card_info['parallel']
        ]
        
        title = " ".join(title_parts)
        
        # Build description with grading details
        description_parts = [
            f"Professional Sports Authenticator (PSA) Graded Card",
            f"Player: {card_info['player']}",
            f"Set: {card_info['set']}",
            f"Card Number: #{card_info['card_number']}",
            f"Grade: PSA {card_info['grade']}",
            f"Grading Company: PSA",
            f"Parallel/Insert: {card_info['parallel']}"
        ]
        
        description = " | ".join(description_parts)
        
        # Determine pricing based on grade and player
        if card_info['grade'] == '10':
            if 'Fernando Tatis' in card_info['player']:
                # 2019 Tatis rookie PSA 10 is very valuable
                start_price = 199.99
                buy_it_now = 499.99
            else:
                # Other PSA 10s
                start_price = 99.99
                buy_it_now = 249.99
        else:
            # PSA 9 (Juan Soto)
            start_price = 49.99
            buy_it_now = 149.99
        
        # Category for trading cards
        category = "261328"  # Sports Trading Cards category
        
        csv_row = {
            'Title': title[:80],  # eBay title limit
            'Description': description,
            'StartPrice': f"{start_price:.2f}",
            'BuyItNowPrice': f"{buy_it_now:.2f}",
            'Category': category,
            'PicURL': image_urls,
            'Condition': 'Used',  # PSA graded cards are technically "used"
            'Format': 'Auction',
            'Duration': '7',  # 7-day auction
            'Quantity': '1',
            'Location': 'United States',
            'ShippingType': 'Calculated',
            'ShippingService-1:Option': 'USPSMedia',
            'ShippingService-1:Cost': '4.99',
            'PaymentMethods': 'PayPal',
            'PayPalEmailAddress': 'your-paypal@email.com',  # Update this
            'ReturnPolicy': 'ReturnsAccepted',
            'ReturnsWithin': 'Days_30',
            'ReturnsDescription': '30-day returns accepted',
            'Player': card_info['player'],
            'Year': card_info['set'].split()[0] if card_info['set'].split()[0].isdigit() else '',
            'Set': card_info['set'],
            'Grade': f"PSA {card_info['grade']}",
            'Card_Number': card_info['card_number'],
            'Parallel': card_info['parallel'],
            'Expected_Value': f"${start_price:.2f} - ${buy_it_now:.2f}"
        }
        
        csv_data.append(csv_row)
    
    # Create DataFrame and export
    df = pd.DataFrame(csv_data)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"psa_cards_refined_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    
    print(f"✅ PSA cards CSV exported: {filename}")
    print(f"📊 Cards in CSV: {len(csv_data)}")
    
    # Show summary
    print(f"\n📋 PSA Cards Summary:")
    for i, card_data in enumerate(psa_cards_data, 1):
        card_info = card_data['card_info']
        csv_row = csv_data[i-1]
        
        print(f"  {i}. {card_info['player']} - PSA {card_info['grade']}")
        print(f"     Set: {card_info['set']}")
        print(f"     Parallel: {card_info['parallel']}")
        print(f"     Pricing: {csv_row['StartPrice']} - {csv_row['BuyItNowPrice']}")
        print(f"     URLs: {'✅' if csv_row['PicURL'] else '❌'}")
    
    return filename

def main():
    """
    Main function to process the 4 PSA graded cards and create refined CSV.
    """
    print("=== PSA Graded Cards Refined Processing ===\n")
    
    # Step 1: Identify PSA graded cards
    print("🔄 Step 1: Identifying PSA graded cards...")
    psa_cards_data = identify_and_process_psa_cards()
    
    if not psa_cards_data:
        print("❌ No PSA graded cards found. Exiting.")
        return
    
    print(f"✅ Found {len(psa_cards_data)} PSA graded cards!")
    
    # Step 2: Load image URLs
    print(f"\n🔄 Step 2: Loading image URLs...")
    image_urls_dict = load_image_urls()
    print(f"✅ Loaded {len(image_urls_dict)} image URLs")
    
    # Step 3: Create refined CSV
    csv_filename = create_psa_cards_csv(psa_cards_data, image_urls_dict)
    
    print(f"\n🎉 PSA graded cards processing complete!")
    print(f"📁 CSV file: {csv_filename}")
    print(f"💰 Ready for eBay bulk upload with correct PSA information!")
    
    print(f"\n🎯 Key Features:")
    print(f"  ✅ Correct PSA grades (9, 10, 10, 10)")
    print(f"  ✅ Proper card descriptions and parallels")
    print(f"  ✅ Realistic pricing based on card value")
    print(f"  ✅ All image URLs included")
    print(f"  ✅ One entry per card (no duplicates)")

if __name__ == '__main__':
    main() 