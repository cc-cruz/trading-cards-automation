#!/usr/bin/env python3

import os
import sys
from src.enhanced_card_processor import (
    _extract_player_from_filename, 
    _extract_card_details_enhanced,
    _quick_graded_card_detection,
    quick_graded_check
)
import io
from google.cloud import vision
import json
from google.oauth2.credentials import Credentials

def test_psa_card_detection(image_path):
    """Test PSA graded card detection and extraction on a single card image."""
    
    print(f"=== Testing PSA Graded Card Detection ===")
    print(f"Image: {os.path.basename(image_path)}")
    print("-" * 60)
    
    # 1. Extract player name from filename
    player_name = _extract_player_from_filename(image_path)
    print(f"🏷️  Player from filename: {player_name}")
    
    # 2. Quick graded check (without full OCR processing)
    print(f"\n🔍 Quick Graded Card Check:")
    is_graded_quick = quick_graded_check(image_path)
    print(f"  Quick detection result: {'🏆 PSA GRADED' if is_graded_quick else '📄 Raw Card'}")
    
    # 3. Initialize Vision API client for full OCR
    try:
        if not os.path.exists('token.json'):
            print("❌ token.json not found. Please run authentication first.")
            return
            
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        client = vision.ImageAnnotatorClient(credentials=creds)
        
        print("✅ Vision API client initialized")
        
    except Exception as e:
        print(f"❌ Error initializing Vision API: {e}")
        return
    
    # 4. Get full OCR text
    try:
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Vision API error: {response.error.message}")
            return
            
        raw_text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        print(f"\n📄 Raw OCR Text (first 500 chars):")
        print("-" * 40)
        print(raw_text[:500] + "..." if len(raw_text) > 500 else raw_text)
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error getting OCR text: {e}")
        return
    
    # 5. Test graded detection on OCR text
    print(f"\n🔍 Graded Detection Analysis:")
    is_graded_ocr = _quick_graded_card_detection(raw_text)
    print(f"  OCR-based detection: {'🏆 PSA GRADED' if is_graded_ocr else '📄 Raw Card'}")
    
    # Show detection indicators found
    psa_indicators = [
        (r'\bPSA\s+\d+\b', 'PSA Grade (e.g., PSA 10)'),
        (r'\bPROFESSIONAL\s+SPORTS\s+AUTHENTICATOR\b', 'Full PSA Name'),
        (r'\bCERT\s*#?\s*\d{8,}\b', 'Certification Number'),
        (r'\bPSA\b', 'PSA Mention'),
        (r'\bGRADE\s*:?\s*\d+\b', 'Grade Reference'),
        (r'QR', 'QR Code Indicator'),
    ]
    
    print(f"\n🔬 Detection Indicators Found:")
    import re
    for pattern, description in psa_indicators:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        if matches:
            print(f"  ✅ {description}: {matches}")
        else:
            print(f"  ❌ {description}: Not found")
    
    # 6. Extract card details using enhanced processor
    print(f"\n🔍 Enhanced Extraction Results:")
    print("-" * 40)
    
    card_details = _extract_card_details_enhanced(raw_text, player_name)
    
    # Display results with special formatting for graded cards
    for key, value in card_details.items():
        if value:
            if key == 'graded' and value:
                print(f"  🏆 {key.title()}: {value}")
            elif key in ['grade', 'grading_company', 'cert_number'] and value:
                print(f"  🏆 {key.replace('_', ' ').title()}: {value}")
            else:
                print(f"  ✅ {key.replace('_', ' ').title()}: {value}")
        else:
            print(f"  ❌ {key.replace('_', ' ').title()}: Not found")
    
    # 7. Show confidence and search query preview
    required_fields = ['player', 'set', 'year']
    found_fields = [k for k in required_fields if card_details.get(k)]
    confidence = len(found_fields) / len(required_fields)
    
    if card_details.get('parallel') or card_details.get('features'):
        confidence = min(1.0, confidence + 0.2)
    
    # Bonus confidence for graded cards (they're usually more complete)
    if card_details.get('graded'):
        confidence = min(1.0, confidence + 0.1)
    
    print(f"\n📊 Extraction Confidence: {confidence:.2f}")
    
    # 8. Preview eBay search query
    from src.price_finder import _build_search_query
    search_query = _build_search_query(card_details)
    print(f"🔍 eBay Search Query: {search_query}")
    
    # 9. Special analysis for graded cards
    if card_details.get('graded'):
        print(f"\n🏆 PSA Graded Card Analysis:")
        print("-" * 30)
        print(f"  Grade: {card_details.get('grade', 'Not detected')}")
        print(f"  Cert #: {card_details.get('cert_number', 'Not detected')}")
        print(f"  Expected higher pricing due to grading")
        print(f"  Search query includes PSA grade for accuracy")
    
    print(f"\n✅ PSA card detection test complete!")

def main():
    """Main function to test PSA card detection."""
    
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
    test_psa_card_detection(image_path)

if __name__ == '__main__':
    main() 