#!/usr/bin/env python3

import os
from test_single_card_ocr import test_single_card_ocr

def main():
    # Test different cards to see parallel extraction
    test_cards = [
        'images/jackson-merrill-2-front.jpg',  # Might have parallel info
        'images/shota-imanaga-back.jpg',       # Different player
        'images/chourio-salas-front.jpg',      # Another player
        'images/elly-delacruz-front.jpg'       # Another option
    ]
    
    for card_path in test_cards:
        if os.path.exists(card_path):
            print(f"\n{'='*60}")
            print(f"Testing: {os.path.basename(card_path)}")
            print('='*60)
            test_single_card_ocr(card_path)
            break
    else:
        print("None of the test cards found, using first available...")
        images = [f for f in os.listdir('images') if f.endswith('.jpg')]
        if images:
            test_single_card_ocr(os.path.join('images', images[0]))

if __name__ == "__main__":
    main() 