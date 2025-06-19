#!/usr/bin/env python3

import os
import sys
from src.utils.enhanced_card_processor import _extract_player_from_filename, _extract_card_details_enhanced
import io
from google.cloud import vision
import json
from google.oauth2.credentials import Credentials

def test_single_card_ocr(image_path):
    """Test OCR extraction on a single card image with detailed output."""
    
    print(f"=== Testing OCR Extraction ===")
    print(f"Image: {os.path.basename(image_path)}")
    print("-" * 50)
    
    # 1. Extract player name from filename
    player_name = _extract_player_from_filename(image_path)
    print(f"🏷️  Player from filename: {player_name}")
    
    # 2. Initialize Vision API client
    creds = None

    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/cloud-platform'
    ]

    # 1️⃣ OAuth token.json
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            creds = None

    # 2️⃣ Service-account key
    if not creds and os.path.exists('credentials.json'):
        try:
            from google.oauth2 import service_account
            with open('credentials.json', 'r') as f:
                secret_data = json.load(f)
            if secret_data.get('type') == 'service_account':
                creds = service_account.Credentials.from_service_account_file(
                    'credentials.json', scopes=SCOPES
                )
        except Exception:
            creds = None

    # 3️⃣ Default creds
    if creds:
        client = vision.ImageAnnotatorClient(credentials=creds)
    else:
        client = vision.ImageAnnotatorClient()
    
    print("✅ Vision API client initialized")
    
    # 3. Get OCR text
    try:
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Vision API error: {response.error.message}")
            return
            
        raw_text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        print(f"\n📄 Raw OCR Text:")
        print("-" * 30)
        print(raw_text)
        print("-" * 30)
        
    except Exception as e:
        print(f"❌ Error getting OCR text: {e}")
        return
    
    # 4. Extract card details using enhanced processor
    print(f"\n🔍 Enhanced Extraction Results:")
    print("-" * 40)
    
    card_details = _extract_card_details_enhanced(raw_text, player_name)
    
    for key, value in card_details.items():
        if value:
            if key == 'graded' and value:
                print(f"  🏆 {key.title()}: {value}")
            else:
                print(f"  ✅ {key.title()}: {value}")
        else:
            print(f"  ❌ {key.title()}: Not found")
    
    # 5. Show confidence and search query preview
    required_fields = ['player', 'set', 'year']
    found_fields = [k for k in required_fields if card_details.get(k)]
    confidence = len(found_fields) / len(required_fields)
    
    if card_details.get('parallel') or card_details.get('features'):
        confidence = min(1.0, confidence + 0.2)
    
    print(f"\n📊 Extraction Confidence: {confidence:.2f}")
    
    # 6. Preview eBay search query
    from src.utils.price_finder import _build_search_query
    search_query = _build_search_query(card_details)
    print(f"🔍 eBay Search Query: {search_query}")
    
    # 7. Show detailed analysis
    print(f"\n🔬 Detailed Analysis:")
    print("-" * 25)
    
    # Check for parallel indicators
    parallel_indicators = ['1/1', '24/99', 'SUPERFRACTOR', 'REFRACTOR', 'CHROME', 'PRIZM', 'AUTO', 'ROOKIE', 'RC']
    found_indicators = [indicator for indicator in parallel_indicators if indicator in raw_text.upper()]
    
    if found_indicators:
        print(f"  🎯 Parallel indicators found: {', '.join(found_indicators)}")
    else:
        print(f"  ⚠️  No obvious parallel indicators found")
    
    # Check for manufacturer keywords
    manufacturers = ['TOPPS', 'PANINI', 'BOWMAN', 'DONRUSS', 'UPPER DECK', 'FLEER']
    found_manufacturers = [mfg for mfg in manufacturers if mfg in raw_text.upper()]
    
    if found_manufacturers:
        print(f"  🏭 Manufacturers found: {', '.join(found_manufacturers)}")
    else:
        print(f"  ⚠️  No clear manufacturer found")
    
    # Check for years
    import re
    years = re.findall(r'\b(20[0-2]\d)\b', raw_text)
    if years:
        print(f"  📅 Years found: {', '.join(set(years))}")
    else:
        print(f"  ⚠️  No recent years found")
    
    print(f"\n✅ Single card test complete!")
    return card_details

def main():
    """Main function to test a single card."""
    
    # Check if images directory exists
    if not os.path.exists('images'):
        print("❌ No 'images' directory found. Please run the main pipeline first to download images.")
        return
    
    # Get list of available images
    image_files = [f for f in os.listdir('images') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("❌ No image files found in 'images' directory.")
        return
    
    print("Available images:")
    for i, filename in enumerate(image_files[:10], 1):  # Show first 10
        print(f"  {i}. {filename}")
    
    if len(image_files) > 10:
        print(f"  ... and {len(image_files) - 10} more")
    
    # Let user choose an image or default to first one
    print(f"\nChoose an image to test (1-{min(10, len(image_files))}) or press Enter for first image:")
    
    try:
        choice = input().strip()
        if choice:
            index = int(choice) - 1
            if 0 <= index < min(10, len(image_files)):
                selected_file = image_files[index]
            else:
                print("Invalid choice, using first image.")
                selected_file = image_files[0]
        else:
            selected_file = image_files[0]
    except (ValueError, KeyboardInterrupt):
        print("Using first image.")
        selected_file = image_files[0]
    
    image_path = os.path.join('images', selected_file)
    
    # Test the selected image
    test_single_card_ocr(image_path)

if __name__ == "__main__":
    main() 