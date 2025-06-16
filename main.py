import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.drive_downloader import download_from_drive
from src.enhanced_card_processor import process_all_images_enhanced as process_all_images
from src.price_finder import research_all_prices

def get_image_urls_for_card(card_data, image_urls_dict):
    """
    Get image URLs for a specific card based on the card data.
    
    Args:
        card_data (dict): Card information with player name, etc.
        image_urls_dict (dict): Dictionary of filename -> URL mappings
    
    Returns:
        str: Pipe-separated URLs for this card, or empty string if none found
    """
    if not image_urls_dict:
        return ""
    
    card_urls = []
    
    # Try to match based on player name
    player_name = card_data.get('player', '').lower()
    if player_name:
        # Convert player name to filename format (e.g., "Paul Skenes" -> "paul-skenes")
        player_filename = player_name.replace(' ', '-').replace('.', '').lower()
        
        # Look for matching images
        for filename, url in image_urls_dict.items():
            filename_lower = filename.lower()
            if player_filename in filename_lower:
                card_urls.append(url)
    
    # If no player-based match, try to match by any available info
    if not card_urls:
        # Try matching by set or other identifiers
        for key in ['set', 'manufacturer']:
            if card_data.get(key):
                search_term = card_data[key].lower().replace(' ', '-')
                for filename, url in image_urls_dict.items():
                    if search_term in filename.lower():
                        card_urls.append(url)
                        break
    
    # Return pipe-separated URLs (eBay format for multiple images)
    return "|".join(card_urls) if card_urls else ""

def load_gcs_image_urls():
    """
    Load image URLs from the GCS URL generator output file.
    
    Returns:
        dict: Dictionary of filename -> URL mappings, or empty dict if file not found
    """
    try:
        import json
        with open('image_urls.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  image_urls.json not found. Run src/gcs_url_generator.py first to get image URLs.")
        return {}
    except Exception as e:
        print(f"⚠️  Error loading image URLs: {e}")
        return {}

def export_final_csv(priced_cards):
    """
    Builds and exports the final CSV file for eBay bulk upload.
    Uses eBay's official Seller Hub Reports format with all required fields.
    Automatically includes image URLs from Google Cloud Storage.
    """
    print("Step 4: Building eBay-compliant CSV...")
    
    # Load image URLs from GCS
    print("🖼️  Loading image URLs from Google Cloud Storage...")
    image_urls_dict = load_gcs_image_urls()
    if image_urls_dict:
        print(f"✅ Loaded {len(image_urls_dict)} image URLs")
    else:
        print("⚠️  No image URLs loaded - listings will be created without images")
    
    # eBay's REQUIRED columns for bulk upload
    columns = [
        "Action", "Custom label (SKU)", "Category ID", "Title", "Condition ID", 
        "P:UPC", "Item photo URL", "Format", "Description", "Duration", 
        "Start price", "Quantity", "Location", "Shipping profile name", 
        "Return profile name", "Payment profile name",
        # Item specifics for trading cards (C: prefix indicates category-specific)
        "C:Brand", "C:Player", "C:Set", "C:Year", "C:Card Number", 
        "C:Parallel/Variety", "C:Features"
    ]
    
    rows = []
    for i, card in enumerate(priced_cards):
        # Build eBay-compliant title (80 char max)
        title_parts = []
        if card.get('year'):
            title_parts.append(str(card['year']))
        if card.get('set'):
            title_parts.append(card['set'])
        if card.get('player'):
            title_parts.append(card['player'])
        if card.get('card_number'):
            title_parts.append(f"#{card['card_number']}")
        if card.get('parallel'):
            title_parts.append(card['parallel'])
        
        title = " ".join(title_parts)[:80] if title_parts else "Trading Card"
        
        # Build description with all card details
        description_parts = []
        if card.get('player'):
            description_parts.append(f"Player: {card['player']}")
        if card.get('set'):
            description_parts.append(f"Set: {card['set']}")
        if card.get('year'):
            description_parts.append(f"Year: {card['year']}")
        if card.get('card_number'):
            description_parts.append(f"Card Number: {card['card_number']}")
        if card.get('parallel'):
            description_parts.append(f"Parallel: {card['parallel']}")
        if card.get('manufacturer'):
            description_parts.append(f"Manufacturer: {card['manufacturer']}")
        
        description = "<br>".join(description_parts) if description_parts else "Trading Card"
        
        # Determine price - use eBay research or default
        start_price = "9.99"  # Default starting price
        if card.get('pricing_data') and card['pricing_data'].get('average_sold_price'):
            try:
                price = float(card['pricing_data']['average_sold_price'])
                start_price = f"{price:.2f}"
            except (ValueError, TypeError):
                start_price = "9.99"
        
        # Determine manufacturer/brand
        brand = "Unbranded"
        if card.get('set'):
            set_name = card['set'].upper()
            if 'TOPPS' in set_name:
                brand = "Topps"
            elif 'PANINI' in set_name:
                brand = "Panini"
            elif 'DONRUSS' in set_name:
                brand = "Donruss"
            elif 'BOWMAN' in set_name:
                brand = "Bowman"
            elif 'UPPER DECK' in set_name:
                brand = "Upper Deck"
        
        # Get image URLs for this card
        item_photo_urls = get_image_urls_for_card(card, image_urls_dict)
        
        row = {
            # REQUIRED eBay fields
            "Action": "Add",
            "Custom label (SKU)": f"CARD-{i+1:03d}",  # Unique SKU
            "Category ID": "213",  # Sports Trading Cards category
            "Title": title,
            "Condition ID": "1000",  # New condition
            "P:UPC": "Does not apply",  # Most cards don't have UPC
            "Item photo URL": item_photo_urls,  # GCS URLs
            "Format": "FixedPrice",
            "Description": description,
            "Duration": "GTC",  # Good Till Cancelled
            "Start price": start_price,
            "Quantity": "1",
            "Location": "United States",  # Default location
            "Shipping profile name": "Free Domestic Shipping",  # Must match business policy
            "Return profile name": "30 Day Returns",  # Must match business policy  
            "Payment profile name": "Standard Payment",  # Must match business policy
            
            # Item specifics for trading cards
            "C:Brand": brand,
            "C:Player": card.get('player', ''),
            "C:Set": card.get('set', ''),
            "C:Year": card.get('year', ''),
            "C:Card Number": card.get('card_number', ''),
            "C:Parallel/Variety": card.get('parallel', ''),
            "C:Features": card.get('features', '')
        }
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows, columns=columns)
    
    # Export to CSV
    output_filename = "ebay_bulk_upload.csv"
    df.to_csv(output_filename, index=False)
    
    # Count cards with images
    cards_with_images = sum(1 for row in rows if row["Item photo URL"])
    
    print(f"✅ eBay-compliant CSV export complete!")
    print(f"📁 File saved as '{output_filename}'")
    print(f"📊 Generated {len(rows)} listings ready for eBay Seller Hub Reports upload")
    print(f"🖼️  {cards_with_images}/{len(rows)} cards have images attached")
    print(f"\n⚠️  IMPORTANT NOTES:")
    print(f"   • Business Policies configured:")
    print(f"     - 'Free Domestic Shipping' (shipping policy) ✅")
    print(f"     - '30 Day Returns' (return policy) ✅")
    print(f"     - 'Standard Payment' (payment policy) ✅")
    if cards_with_images < len(rows):
        print(f"   • {len(rows) - cards_with_images} cards missing images - check GCS URLs")
    print(f"   • Upload via: Seller Hub > Reports > Upload > Upload template")

def main():
    """
    Main orchestration function to run the trading card listing pipeline.
    Follows the execution flow and approximate timing targets.
    """
    print("=== Trading Card Automation Pipeline ===\n")
    
    # Step 1: Download images from Google Drive (Target: 5 minutes)
    print("🔄 Step 1: Downloading all images from Google Drive...")
    images = download_from_drive()      
    
    if not images:
        print("No images downloaded. Exiting pipeline.")
        return
    
    print(f"✅ Downloaded {len(images)} images successfully!")
    
    # Step 2: Process images with OCR (Target: 15 minutes)
    print("\n🔄 Step 2: Processing images with Google Vision API...")
    cards = process_all_images(images)  
    
    if not cards:
        print("No cards processed. Exiting pipeline.")
        return
    
    print(f"✅ Processed {len(cards)} cards with OCR!")
    
    # Show progress every 5 cards during processing
    print("\n📊 Card Processing Results (showing every 5th card):")
    for i, card in enumerate(cards):
        if (i + 1) % 5 == 0 or i == len(cards) - 1:
            print(f"  Card {i+1}/{len(cards)}: {card.get('player', 'Unknown')} - {card.get('set', 'Unknown Set')} ({card.get('year', 'Unknown Year')})")
    
    # Step 3: Research prices on eBay (Target: 8 minutes)
    print(f"\n🔄 Step 3: Researching eBay prices for {len(cards)} cards...")
    priced_cards = research_all_prices(cards) 
    
    # Show pricing progress every 5 cards
    print("\n💰 Pricing Results (showing every 5th card):")
    successful_pricing = 0
    for i, card in enumerate(priced_cards):
        if card.get('pricing_data'):
            successful_pricing += 1
        if (i + 1) % 5 == 0 or i == len(priced_cards) - 1:
            price_info = "No price found"
            if card.get('pricing_data'):
                price_info = f"${card['pricing_data']['average_sold_price']}"
            print(f"  Card {i+1}/{len(priced_cards)}: {card.get('player', 'Unknown')} - {price_info}")
    
    # Step 4: Build the final CSV for upload (Target: 2 minutes)
    print(f"\n🔄 Step 4: Generating final CSV with 25 rows...")
    
    # Limit to 25 cards as requested
    final_cards = priced_cards[:25]
    export_final_csv(final_cards)

    print("\n🎉 Trading card automation pipeline finished successfully!")
    
    # Print summary
    successful_cards = [c for c in final_cards if c.get('pricing_data')]
    print(f"\nSUMMARY:")
    print(f"- Total images downloaded: {len(images)}")
    print(f"- Cards processed with OCR: {len(cards)}")
    print(f"- Cards included in final CSV: {len(final_cards)}")
    print(f"- Cards with successful pricing: {len(successful_cards)}")
    print(f"- Pricing success rate: {len(successful_cards)/len(final_cards)*100:.1f}%")
    print(f"- Final CSV: ebay_bulk_upload.csv ({len(final_cards)} rows)")

if __name__ == "__main__":
    main() 