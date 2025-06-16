#!/usr/bin/env python3

import os
import sys
from src.utils.enhanced_card_processor import (
    _extract_player_from_filename, 
    _quick_graded_card_detection,
    quick_graded_check
)
import io
from google.cloud import vision
import json
from google.oauth2.credentials import Credentials
from tqdm import tqdm

def scan_collection_for_psa_cards():
    """Scan the entire collection for PSA graded cards."""
    
    print("=== Scanning Entire Collection for PSA Graded Cards ===")
    print("-" * 60)
    
    # Check if images directory exists
    if not os.path.exists('images'):
        print("❌ No 'images' directory found. Please run the main pipeline first to download images.")
        return
    
    # Get all image files
    image_files = [f for f in os.listdir('images') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print("❌ No image files found in 'images' directory.")
        return
    
    print(f"🔍 Scanning {len(image_files)} cards for PSA grading...")
    
    # Initialize Vision API client
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
        
    except Exception as e:
        print(f"❌ Error initializing Vision API: {e}")
        return
    
    # Track results
    psa_cards = []
    raw_cards = []
    error_cards = []
    
    # Scan each card
    for image_file in tqdm(image_files, desc="Scanning cards"):
        image_path = os.path.join('images', image_file)
        
        try:
            # Extract player name from filename
            player_name = _extract_player_from_filename(image_path)
            
            # Quick OCR scan for PSA indicators
            with io.open(image_path, 'rb') as img_file:
                content = img_file.read()
            
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            
            if response.error.message:
                error_cards.append({
                    'file': image_file,
                    'player': player_name,
                    'error': response.error.message
                })
                continue
                
            text = response.full_text_annotation.text if response.full_text_annotation else ""
            
            # Check for PSA grading
            is_graded = _quick_graded_card_detection(text)
            
            card_info = {
                'file': image_file,
                'player': player_name or 'Unknown',
                'text_preview': text[:200].replace('\n', ' ') if text else 'No text detected'
            }
            
            if is_graded:
                # Extract additional PSA details for graded cards
                import re
                
                # Look for PSA grade
                grade_match = re.search(r'PSA\s+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
                if grade_match:
                    card_info['grade'] = grade_match.group(1)
                
                # Look for cert number
                cert_match = re.search(r'CERT\s*#?\s*(\d{8,})', text, re.IGNORECASE)
                if cert_match:
                    card_info['cert_number'] = cert_match.group(1)
                
                psa_cards.append(card_info)
            else:
                raw_cards.append(card_info)
                
        except Exception as e:
            error_cards.append({
                'file': image_file,
                'player': player_name or 'Unknown',
                'error': str(e)
            })
    
    # Display results
    print(f"\n📊 Collection Scan Results:")
    print(f"  Total cards scanned: {len(image_files)}")
    print(f"  🏆 PSA Graded cards: {len(psa_cards)}")
    print(f"  📄 Raw cards: {len(raw_cards)}")
    print(f"  ❌ Error cards: {len(error_cards)}")
    
    # Show PSA graded cards
    if psa_cards:
        print(f"\n🏆 PSA GRADED CARDS FOUND:")
        print("=" * 50)
        for i, card in enumerate(psa_cards, 1):
            print(f"{i}. {card['file']}")
            print(f"   Player: {card['player']}")
            if card.get('grade'):
                print(f"   Grade: PSA {card['grade']}")
            if card.get('cert_number'):
                print(f"   Cert #: {card['cert_number']}")
            print(f"   Preview: {card['text_preview'][:100]}...")
            print("-" * 30)
    else:
        print(f"\n📄 No PSA graded cards found in collection.")
        print("All cards appear to be raw (ungraded) cards.")
    
    # Show sample raw cards
    if raw_cards:
        print(f"\n📄 Sample Raw Cards (first 5):")
        print("-" * 40)
        for i, card in enumerate(raw_cards[:5], 1):
            print(f"{i}. {card['file']} - {card['player']}")
    
    # Show errors if any
    if error_cards:
        print(f"\n❌ Cards with Processing Errors:")
        print("-" * 40)
        for card in error_cards[:5]:  # Show first 5 errors
            print(f"  {card['file']} - {card['player']}: {card['error']}")
        if len(error_cards) > 5:
            print(f"  ... and {len(error_cards) - 5} more errors")
    
    # Summary recommendations
    print(f"\n💡 Recommendations:")
    if psa_cards:
        print(f"  - PSA graded cards found! These will have higher pricing accuracy")
        print(f"  - Graded cards typically sell for premium prices")
        print(f"  - Make sure to include PSA grade in eBay listings")
    else:
        print(f"  - No PSA graded cards detected in current collection")
        print(f"  - All cards appear to be raw cards")
        print(f"  - Consider getting valuable cards professionally graded")
    
    print(f"\n✅ Collection scan complete!")
    
    return {
        'psa_cards': psa_cards,
        'raw_cards': raw_cards,
        'error_cards': error_cards,
        'total_scanned': len(image_files)
    }

def main():
    """Main function to scan collection for PSA cards."""
    results = scan_collection_for_psa_cards()
    
    if results and results['psa_cards']:
        print(f"\n🎯 Next Steps for PSA Cards:")
        print(f"  1. Run main pipeline - PSA cards will get enhanced extraction")
        print(f"  2. PSA grades will be included in eBay search queries")
        print(f"  3. Expect higher pricing for graded cards")
        print(f"  4. Certification numbers will be tracked for authenticity")

if __name__ == '__main__':
    main() 