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

def identify_psa_graded_cards():
    """
    Identify the 4 unique PSA graded cards based on the user's description:
    1. Juan Soto PSA 9 Aqua Equinox Refractor
    2. Fernando Tatis PSA 10 Rookie
    3. Chourio/Salas International Impact PSA 10
    4. Jackson Merrill Chrome Cosmic PSA 10
    """
    
    if not os.path.exists('images'):
        print("❌ No 'images' directory found.")
        return []
    
    all_images = [f for f in os.listdir('images') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Define the 4 PSA graded cards based on filenames
    psa_card_patterns = {
        'juan-soto': {
            'description': 'Juan Soto PSA 9 Aqua Equinox Refractor',
            'expected_files': ['juan-soto-front.jpg', 'juan-soto-back.jpg']
        },
        'fernando-tatis': {
            'description': 'Fernando Tatis PSA 10 Rookie',
            'expected_files': ['fernando-tatis-front.jpg', 'fernando-tatis-back.jpg']
        },
        'chourio-salas': {
            'description': 'Chourio/Salas International Impact PSA 10',
            'expected_files': ['chourio-salas-front.jpg', 'chourio-salas-back.jpg']
        },
        'jackson-merrill': {
            'description': 'Jackson Merrill Chrome Cosmic PSA 10',
            'expected_files': ['jackson-merrill-front.jpg', 'jackson-merrill-back.jpg', 'jackson-merrill-2-front.jpg']
        }
    }
    
    psa_images = []
    found_cards = []
    
    print("🔍 Identifying PSA Graded Cards:")
    print("-" * 40)
    
    for card_key, card_info in psa_card_patterns.items():
        found_files = []
        for expected_file in card_info['expected_files']:
            if expected_file in all_images:
                found_files.append(expected_file)
                psa_images.append(os.path.join('images', expected_file))
        
        if found_files:
            found_cards.append({
                'card': card_info['description'],
                'files': found_files
            })
            print(f"✅ {card_info['description']}")
            for file in found_files:
                print(f"   📁 {file}")
        else:
            print(f"❌ {card_info['description']} - No matching files found")
    
    print(f"\n📊 Summary:")
    print(f"  PSA cards found: {len(found_cards)}/4")
    print(f"  Total image files: {len(psa_images)}")
    
    return psa_images, found_cards

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

def get_image_urls_for_card(card_data, image_urls_dict):
    """
    Get image URLs for a specific card based on the card data.
    Returns pipe-separated URLs for eBay format.
    """
    if not image_urls_dict:
        return ""
    
    card_urls = []
    
    # Try to match based on player name
    player_name = card_data.get('player', '').lower()
    if player_name:
        # Convert player name to filename format (e.g., "Juan Soto" -> "juan-soto")
        player_filename = player_name.replace(' ', '-').replace('.', '').lower()
        
        # Look for matching images
        for filename, url in image_urls_dict.items():
            filename_lower = filename.lower()
            if player_filename in filename_lower:
                card_urls.append(url)
    
    # Return pipe-separated URLs (eBay format for multiple images)
    return "|".join(card_urls) if card_urls else ""

def export_psa_cards_csv(priced_cards, image_urls_dict):
    """
    Export PSA graded cards to CSV format for eBay bulk upload.
    """
    print("\n🔄 Step 4: Generating PSA cards CSV...")
    
    csv_data = []
    
    for card in priced_cards:
        # Get image URLs for this card
        image_urls = get_image_urls_for_card(card, image_urls_dict)
        
        # Build title with PSA grading info
        title_parts = []
        
        if card.get('year'):
            title_parts.append(str(card['year']))
        
        if card.get('set'):
            title_parts.append(card['set'])
        
        if card.get('player'):
            title_parts.append(card['player'])
        
        if card.get('card_number'):
            title_parts.append(f"#{card['card_number']}")
        
        # Add PSA grading info (CRITICAL for graded cards)
        if card.get('graded') and card.get('grade'):
            title_parts.append(f"PSA {card['grade']}")
        
        if card.get('parallel'):
            title_parts.append(card['parallel'])
        
        if card.get('features'):
            title_parts.append(card['features'])
        
        title = " ".join(title_parts)
        
        # Build description with grading details
        description_parts = [
            f"Professional Sports Authenticator (PSA) Graded Card",
            f"Player: {card.get('player', 'N/A')}",
            f"Year: {card.get('year', 'N/A')}",
            f"Set: {card.get('set', 'N/A')}",
        ]
        
        if card.get('graded'):
            description_parts.extend([
                f"Grade: PSA {card.get('grade', 'N/A')}",
                f"Grading Company: {card.get('grading_company', 'PSA')}",
            ])
            if card.get('cert_number'):
                description_parts.append(f"Certification Number: {card['cert_number']}")
        
        if card.get('parallel'):
            description_parts.append(f"Parallel/Insert: {card['parallel']}")
        
        if card.get('features'):
            description_parts.append(f"Special Features: {card['features']}")
        
        description = " | ".join(description_parts)
        
        # Determine pricing
        if card.get('pricing_data'):
            start_price = max(0.99, card['pricing_data']['listing_price'] * 0.8)  # Start at 80% of listing price
            buy_it_now = card['pricing_data']['listing_price']
        else:
            # Default pricing for graded cards (they're typically valuable)
            start_price = 9.99
            buy_it_now = 49.99
        
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
            'Player': card.get('player', ''),
            'Year': card.get('year', ''),
            'Set': card.get('set', ''),
            'Grade': f"PSA {card.get('grade', '')}" if card.get('graded') else '',
            'Cert_Number': card.get('cert_number', ''),
            'Search_Query': card.get('search_query', ''),
            'Avg_Sold_Price': card.get('pricing_data', {}).get('average_sold_price', '') if card.get('pricing_data') else '',
            'Sample_Size': card.get('pricing_data', {}).get('sample_size', '') if card.get('pricing_data') else ''
        }
        
        csv_data.append(csv_row)
    
    # Create DataFrame and export
    df = pd.DataFrame(csv_data)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"psa_cards_ebay_upload_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    
    print(f"✅ PSA cards CSV exported: {filename}")
    print(f"📊 Cards in CSV: {len(csv_data)}")
    
    # Show summary
    print(f"\n📋 PSA Cards Summary:")
    for i, card in enumerate(priced_cards, 1):
        price_info = "No pricing data"
        if card.get('pricing_data'):
            price_info = f"${card['pricing_data']['average_sold_price']} avg (${card['pricing_data']['listing_price']} list)"
        
        grade_info = f"PSA {card.get('grade', 'Unknown')}" if card.get('graded') else "Not graded"
        
        print(f"  {i}. {card.get('player', 'Unknown')} - {grade_info} - {price_info}")
    
    return filename

def main():
    """
    Main function to process only PSA graded cards and create CSV.
    """
    print("=== PSA Graded Cards Processing Pipeline ===\n")
    
    # Step 1: Identify PSA graded card images
    print("🔄 Step 1: Identifying PSA graded cards...")
    psa_images, found_cards = identify_psa_graded_cards()
    
    if not psa_images:
        print("❌ No PSA graded cards found. Exiting.")
        return
    
    print(f"✅ Found {len(found_cards)} PSA graded cards with {len(psa_images)} image files!")
    
    # Step 2: Process images with enhanced OCR
    print(f"\n🔄 Step 2: Processing {len(psa_images)} PSA card images...")
    cards = process_all_images_enhanced(psa_images)
    
    if not cards:
        print("❌ No cards processed. Exiting.")
        return
    
    print(f"✅ Processed {len(cards)} PSA card images!")
    
    # Show processing results
    print(f"\n📊 PSA Card Processing Results:")
    graded_count = sum(1 for card in cards if card.get('graded'))
    print(f"  Cards with grading detected: {graded_count}/{len(cards)}")
    
    for card in cards:
        grade_info = f"PSA {card.get('grade')}" if card.get('graded') and card.get('grade') else "Grade not detected"
        print(f"  • {card.get('player', 'Unknown')}: {grade_info}")
    
    # Step 3: Research prices on eBay
    print(f"\n🔄 Step 3: Researching eBay prices for PSA cards...")
    priced_cards = research_all_prices(cards)
    
    # Step 4: Load image URLs
    print(f"\n🔄 Loading image URLs...")
    image_urls_dict = load_image_urls()
    print(f"✅ Loaded {len(image_urls_dict)} image URLs")
    
    # Step 5: Export to CSV
    csv_filename = export_psa_cards_csv(priced_cards, image_urls_dict)
    
    print(f"\n🎉 PSA graded cards processing complete!")
    print(f"📁 CSV file: {csv_filename}")
    print(f"💰 Ready for eBay bulk upload with PSA grading information!")
    
    # Final summary
    successful_pricing = sum(1 for card in priced_cards if card.get('pricing_data'))
    print(f"\nFINAL SUMMARY:")
    print(f"- PSA cards processed: {len(cards)}")
    print(f"- Cards with pricing: {successful_pricing}/{len(priced_cards)}")
    print(f"- CSV ready for upload: {csv_filename}")

if __name__ == '__main__':
    main() 