#!/usr/bin/env python3

import os
from test_single_card_ocr import test_single_card_ocr

def main():
    # Test with Paul Skenes card (should have good parallel/set info)
    image_path = 'images/paul-skenes-back.jpg'
    
    if os.path.exists(image_path):
        print("Testing Paul Skenes card...")
        test_single_card_ocr(image_path)
    else:
        print("Paul Skenes image not found, testing first available image...")
        images = [f for f in os.listdir('images') if f.endswith('.jpg')]
        if images:
            test_single_card_ocr(os.path.join('images', images[0]))
        else:
            print("No images found!")

if __name__ == "__main__":
    main() 