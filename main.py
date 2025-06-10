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
    images = download_from_drive()      
    
    if not images:
        print("No images downloaded. Exiting pipeline.")
        return
    
    # Step 2: Process images with OCR (Target: 15 minutes)
    cards = process_all_images(images)  
    
    if not cards:
        print("No cards processed. Exiting pipeline.")
        return
    
    # Step 3: Research prices on eBay (Target: 8 minutes)
    priced_cards = research_all_prices(cards) 
    
    # Step 4: Build the final CSV for upload (Target: 2 minutes)
    export_final_csv(priced_cards)

    print("\n=== Trading card automation pipeline finished successfully! ===")
    
    # Print summary
    successful_cards = [c for c in priced_cards if c.get('pricing_data')]
    print(f"\nSUMMARY:")
    print(f"- Images processed: {len(cards)}")
    print(f"- Cards with pricing: {len(successful_cards)}")
    print(f"- Success rate: {len(successful_cards)/len(cards)*100:.1f}%")

if __name__ == "__main__":
    main() 