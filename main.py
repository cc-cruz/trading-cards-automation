import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.drive_downloader import download_from_drive
from src.card_processor import process_all_images
from src.price_finder import research_all_prices

def export_final_csv(priced_cards):
    """
    Builds and exports the final CSV file for eBay bulk upload.
    - Creates 25 new rows with the processed data.
    - Auto-populates required fields with sensible defaults.
    - Exports the final DataFrame to a CSV file.
    """
    print("Step 4: Building final CSV...")
    
    # Column structure as specified
    columns = [
        "Title", "Sport", "Purchase Price", "Purchase Date", "Player", "Set", 
        "Year", "Card Manufacturer", "Card Number", "Graded (Y/N)", 
        "Card Condition", "Professional Grader", "Grade", "Certification Number", 
        "Parallel", "Features"
    ]
    
    rows = []
    for card in priced_cards:
        # Build title
        title_parts = []
        if card.get('year'):
            title_parts.append(str(card['year']))
        if card.get('set'):
            title_parts.append(card['set'])
        if card.get('player'):
            title_parts.append(card['player'])
        if card.get('card_number'):
            title_parts.append(f"#{card['card_number']}")
        
        title = " ".join(title_parts) if title_parts else "Trading Card"
        
        # Determine sport (basic heuristic)
        sport = "Sports"  # Default
        if card.get('player'):
            # Could add more sophisticated sport detection here
            sport = "Baseball"  # Most common trading cards
        
        # Get pricing info
        purchase_price = ""
        if card.get('pricing_data') and card['pricing_data'].get('average_sold_price'):
            purchase_price = card['pricing_data']['average_sold_price']
        
        # Determine manufacturer from set name
        manufacturer = ""
        if card.get('set'):
            set_name = card['set'].upper()
            if 'TOPPS' in set_name:
                manufacturer = "Topps"
            elif 'PANINI' in set_name:
                manufacturer = "Panini"
            elif 'DONRUSS' in set_name:
                manufacturer = "Donruss"
            else:
                manufacturer = card['set']
        
        row = {
            "Title": title,
            "Sport": sport,
            "Purchase Price": purchase_price,
            "Purchase Date": datetime.now().strftime("%Y-%m-%d"),
            "Player": card.get('player', ''),
            "Set": card.get('set', ''),
            "Year": card.get('year', ''),
            "Card Manufacturer": manufacturer,
            "Card Number": card.get('card_number', ''),
            "Graded (Y/N)": "N",  # Default assumption
            "Card Condition": "Near Mint",  # Default assumption
            "Professional Grader": "",
            "Grade": "",
            "Certification Number": "",
            "Parallel": "",
            "Features": ""
        }
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows, columns=columns)
    
    # Export to CSV
    output_filename = "ebay_listings.csv"
    df.to_csv(output_filename, index=False)
    
    print(f"CSV export complete. File saved as '{output_filename}'")
    print(f"Generated {len(rows)} listings ready for eBay upload.")

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
    print(f"- Final CSV: ebay_listings.csv ({len(final_cards)} rows)")

if __name__ == "__main__":
    main() 