import os
import re
import io
from google.cloud import vision
from tqdm import tqdm

def _extract_card_details(text):
    """
    Uses heuristics and regex to extract details from OCR text.
    This is a challenging step and may require custom tuning.
    """
    details = {
        "player": None,
        "set": None,
        "year": None,
        "card_number": None,
    }

    # 1. Extract Year
    year_match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
    if year_match:
        details["year"] = year_match.group(0)

    # 2. Extract Card Number
    card_num_match = re.search(r'(?:No\.|#)\s*([A-Z0-9-]+)', text, re.IGNORECASE)
    if card_num_match:
        details["card_number"] = card_num_match.group(1)
    
    # 3. Extract Player and Set (Heuristic-based)
    lines = [line.strip() for line in text.split('\n')]
    all_caps_lines = [line for line in lines if line.isupper() and len(line.split()) in [1, 2, 3] and re.search(r'[A-Z]', line)]
    
    common_words = {'TOPPS', 'PANINI', 'DONRUSS', 'PRIZM', 'SELECT', 'MOSAIC', 'OPTIC', 'SCORE', 'CHROME', 'ROOKIE CARD', 'RC'}
    potential_players = []
    potential_sets = []

    for line in all_caps_lines:
        is_common = False
        for word in common_words:
            if word in line:
                is_common = True
                if len(line.split()) <= 2:
                    potential_sets.append(line)
                break
        if not is_common and len(line) > 3:
            potential_players.append(line)

    if potential_players:
        details["player"] = potential_players[0].title() 
    
    if potential_sets:
        details["set"] = potential_sets[0].title()

    return details

def process_all_images(image_paths):
    """
    Processes a list of image paths using Google Vision API OCR.
    """
    print("Step 2: Processing images with Google Vision API...")

    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or not os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
        print("Error: GOOGLE_APPLICATION_CREDENTIALS not set or file not found.")
        print("Please set it in .env to the path of your service account JSON key.")
        return []
    
    try:
        client = vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"Error initializing Google Vision client: {e}")
        return []

    processed_cards = []
    
    if not image_paths:
        print("No images found to process.")
        return []

    for image_path in tqdm(image_paths, desc="Processing images"):
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            text = response.full_text_annotation.text

            if response.error.message:
                raise Exception(f"{response.error.message}")

            card_details = _extract_card_details(text)
            
            found_fields = [k for k, v in card_details.items() if v is not None]
            confidence = len(found_fields) / len(card_details)
            low_confidence_flags = [k for k, v in card_details.items() if v is None]

            result = {
                'image_path': image_path,
                'player': card_details.get('player'),
                'set': card_details.get('set'),
                'year': card_details.get('year'),
                'card_number': card_details.get('card_number'),
                'extraction_confidence': round(confidence, 2),
                'low_confidence_flags': low_confidence_flags,
                'full_ocr_text': text
            }
            processed_cards.append(result)

        except Exception as e:
            print(f"\nError processing {image_path}: {e}")
            processed_cards.append({
                'image_path': image_path, 'player': None, 'set': None, 'year': None, 'card_number': None,
                'extraction_confidence': 0.0, 'low_confidence_flags': ['all'], 'full_ocr_text': f"Error: {e}"
            })
    
    print("Image processing complete.")
    return processed_cards

if __name__ == '__main__':
    if os.path.exists('images'):
        test_image_paths = sorted([os.path.join('images', f) for f in os.listdir('images') if f.endswith('.jpg')])
        if test_image_paths:
            from dotenv import load_dotenv
            load_dotenv()
            
            results = process_all_images(test_image_paths)
            print("\n--- Processing Results ---")
            for card in results:
                print(f"File: {card['image_path']}")
                print(f"  Player: {card['player']}, Set: {card['set']}, Year: {card['year']}, Num: {card['card_number']}")
                print(f"  Confidence: {card['extraction_confidence']}, Flags: {card['low_confidence_flags']}")
                print("-" * 10)
        else:
            print("No JPGs found in 'images' folder for testing.")
    else:
        print("No 'images' directory found for testing.") 