import os
import re
import io
from google.cloud import vision
from tqdm import tqdm

def _quick_graded_card_detection(text):
    """
    Quick detection to identify if this is a PSA graded card.
    Uses multiple indicators including QR code presence and PSA-specific text.
    Returns True if graded, False otherwise.
    """
    # Primary PSA indicators (most reliable)
    primary_indicators = [
        r'\bPSA\s+\d+\b',  # PSA 10, PSA 9, etc.
        r'\bPROFESSIONAL\s+SPORTS\s+AUTHENTICATOR\b',
        r'\bCERT\s*#?\s*\d{8,}\b',  # PSA cert numbers are typically 8+ digits
        r'\bCERTIFICATION\s*#?\s*\d{8,}\b'
    ]
    
    # Secondary indicators (supportive evidence)
    secondary_indicators = [
        r'\bPSA\b',
        r'\bGRADE\s*:?\s*\d+\b',
        r'\bAUTHENTIC\b',
        r'\bGRADED\b'
    ]
    
    # QR code indicators (PSA cards have QR codes)
    qr_indicators = [
        r'QR',
        r'SCAN',
        r'CODE'
    ]
    
    primary_matches = sum(1 for pattern in primary_indicators if re.search(pattern, text, re.IGNORECASE))
    secondary_matches = sum(1 for pattern in secondary_indicators if re.search(pattern, text, re.IGNORECASE))
    qr_matches = sum(1 for pattern in qr_indicators if re.search(pattern, text, re.IGNORECASE))
    
    # Decision logic: Need at least one primary indicator OR multiple secondary + QR
    if primary_matches >= 1:
        return True
    elif secondary_matches >= 2 and qr_matches >= 1:
        return True
    
    return False

def _detect_psa_graded_card(text):
    """
    Detect if this is a PSA graded card based on OCR text.
    Enhanced version with better pattern matching.
    """
    return _quick_graded_card_detection(text)

def _extract_psa_card_details(text, player_name):
    """
    Specialized extraction for PSA graded cards.
    PSA labels have a very structured format that we can leverage.
    Enhanced to extract all required information from PSA labels.
    """
    details = {
        "player": player_name,
        "set": None,
        "year": None,
        "card_number": None,
        "parallel": None,
        "manufacturer": None,
        "features": None,
        "graded": True,
        "grade": None,
        "grading_company": "PSA",
        "cert_number": None
    }
    
    print(f"🏆 Detected PSA graded card - using enhanced extraction")
    
    # 1. Extract PSA Grade (most critical for pricing)
    grade_patterns = [
        r'PSA\s+(\d+(?:\.\d+)?)',  # PSA 10, PSA 9.5
        r'GRADE\s*:?\s*(\d+(?:\.\d+)?)',  # GRADE: 10
        r'(\d+(?:\.\d+)?)\s+PSA',   # 10 PSA (reverse order)
        r'MINT\s+(\d+)',  # MINT 10
        r'GEM\s+MINT\s+(\d+)'  # GEM MINT 10
    ]
    
    for pattern in grade_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            details["grade"] = match.group(1)
            print(f"  ✅ Grade found: {details['grade']}")
            break
    
    # 2. Extract Certification Number (critical for authenticity)
    cert_patterns = [
        r'CERT\s*#?\s*(\d{8,})',  # CERT #12345678
        r'CERTIFICATION\s*#?\s*(\d{8,})',
        r'PSA\s*#\s*(\d{8,})',  # PSA #12345678
        r'#\s*(\d{8,})',  # Simple # followed by long number
        r'(\d{8,})'  # Any 8+ digit number (fallback)
    ]
    
    for pattern in cert_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            cert_num = match.group(1)
            # Validate it's not a year or other number
            if len(cert_num) >= 8 and not (1900 <= int(cert_num[:4]) <= 2030):
                details["cert_number"] = cert_num
                print(f"  ✅ Cert number found: {details['cert_number']}")
                break
    
    # 3. Extract Year (PSA labels clearly display year)
    year_patterns = [
        r'\b(20[0-2]\d)\s+(?:TOPPS|PANINI|BOWMAN|DONRUSS|FLEER|UPPER)',  # Year before manufacturer
        r'(?:TOPPS|PANINI|BOWMAN|DONRUSS|FLEER|UPPER)\s+(20[0-2]\d)',    # Year after manufacturer
        r'©\s*(20[0-2]\d)',  # Copyright year
        r'\b(20[0-2]\d)\b'  # Any recent year (fallback)
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            details["year"] = match.group(1)
            print(f"  ✅ Year found: {details['year']}")
            break
    
    # 4. Extract Set Name (PSA labels are very precise about sets)
    set_patterns = [
        # Full set names with manufacturer
        r'(?:20\d{2}\s+)?(TOPPS\s+CHROME|BOWMAN\s+CHROME|PANINI\s+PRIZM|TOPPS\s+SERIES|BOWMAN\s+STERLING|TOPPS\s+FINEST|TOPPS\s+HERITAGE)',
        r'(?:20\d{2}\s+)?(?:TOPPS|PANINI|BOWMAN|DONRUSS)\s+([A-Z][A-Z\s]+?)(?:\s+#|\s+RC|\s+AUTO|\s*$)',
        # Standalone premium set names
        r'\b(CHROME|PRIZM|SELECT|MOSAIC|OPTIC|STERLING|FINEST|HERITAGE|SERIES)\b',
        # Manufacturer only (fallback)
        r'\b(TOPPS|PANINI|BOWMAN|DONRUSS|FLEER|UPPER\s+DECK)\b'
    ]
    
    for pattern in set_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            set_name = match.group(1).strip().title()
            if len(set_name) > 3:
                details["set"] = set_name
                print(f"  ✅ Set found: {details['set']}")
                
                # Extract manufacturer from set
                set_upper = set_name.upper()
                if any(brand in set_upper for brand in ['TOPPS', 'BOWMAN']):
                    details["manufacturer"] = "TOPPS"
                elif any(brand in set_upper for brand in ['PANINI', 'PRIZM', 'SELECT', 'MOSAIC', 'OPTIC']):
                    details["manufacturer"] = "PANINI"
                elif 'DONRUSS' in set_upper:
                    details["manufacturer"] = "DONRUSS"
                elif any(brand in set_upper for brand in ['FLEER', 'UPPER']):
                    details["manufacturer"] = "UPPER DECK"
                break
    
    # 5. Extract Card Number (PSA labels show card numbers clearly)
    card_num_patterns = [
        r'#\s*([A-Z]*\d{1,4}[A-Z]?)\b',  # #150, #RC150, #150A
        r'NO\.\s*([A-Z]*\d{1,4}[A-Z]?)',  # NO. 150, NO. RC150
        r'CARD\s*#?\s*([A-Z]*\d{1,4}[A-Z]?)',  # CARD #150
        r'\b([A-Z]{1,3}-?\d{1,4})\b'  # RC-1, BDP-15, etc.
    ]
    
    for pattern in card_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            card_num = match.group(1)
            # Avoid years and cert numbers
            if not (len(card_num) >= 4 and card_num.isdigit() and 1900 <= int(card_num) <= 2030):
                details["card_number"] = card_num
                print(f"  ✅ Card number found: {details['card_number']}")
                break
    
    # 6. Extract Parallel/Insert Information (PSA is very specific)
    parallel_patterns = [
        r'\b(\d+/\d+)\b',  # Numbered parallels like 24/99, 1/1
        r'\b(SUPERFRACTOR|REFRACTOR|GOLD\s+REFRACTOR|SILVER\s+REFRACTOR|BLACK\s+REFRACTOR)\b',
        r'\b(AUTO|AUTOGRAPH|SIGNATURE)\b',
        r'\b(PATCH|JERSEY|RELIC|MEMORABILIA)\b',
        r'\b(RC|ROOKIE|1ST\s+BOWMAN|ROOKIE\s+PATCH\s+AUTO|RPA)\b',
        r'\b(CHROME|PRIZM|REFRACTOR)\s+(?!CARD)',  # Avoid "Chrome Card"
        r'\b(GOLD|SILVER|BLACK|RED|BLUE|GREEN|ORANGE|PURPLE)\s+(?:REFRACTOR|PARALLEL|PRIZM)\b'
    ]
    
    parallel_found = []
    for pattern in parallel_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        parallel_found.extend(matches)
    
    if parallel_found:
        # Remove duplicates and join
        unique_parallels = list(dict.fromkeys(parallel_found))  # Preserves order
        details["parallel"] = " ".join(unique_parallels).title()
        print(f"  ✅ Parallel found: {details['parallel']}")
    
    # 7. Extract Special Features (important for search queries)
    feature_keywords = ['ROOKIE', 'RC', 'AUTO', 'AUTOGRAPH', 'PATCH', 'JERSEY', 'RELIC', 'MEMORABILIA', '1ST BOWMAN', 'FIRST BOWMAN']
    features_found = []
    
    for keyword in feature_keywords:
        if keyword in text.upper():
            features_found.append(keyword)
    
    if features_found:
        details["features"] = ", ".join(set(features_found)).title()
        print(f"  ✅ Features found: {details['features']}")
    
    return details

def _extract_player_from_filename(image_path):
    """
    Extract player name from filename.
    Examples: 
    - 'paul-skenes-front.jpg' -> 'Paul Skenes'
    - 'chourio-salas-back.jpg' -> 'Chourio Salas'
    - 'elly-delacruz-front.jpg' -> 'Elly Delacruz'
    """
    filename = os.path.basename(image_path)
    # Remove extension and front/back/number suffixes
    name_part = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
    
    # Remove common suffixes
    suffixes_to_remove = ['-front', '-back', '-2', '-3', '(1)', '(2)', '(3)']
    for suffix in suffixes_to_remove:
        name_part = name_part.replace(suffix, '')
    
    # Convert hyphens to spaces and title case
    if '-' in name_part:
        player_name = name_part.replace('-', ' ').title()
        return player_name
    
    return None

def _extract_card_details_enhanced(text, player_name):
    """
    Enhanced extraction focusing on set, year, parallel, and card details.
    Uses filename-derived player name as ground truth.
    Includes specialized logic for PSA graded cards.
    """
    details = {
        "player": player_name,  # Use filename as ground truth
        "set": None,
        "year": None,
        "card_number": None,
        "parallel": None,
        "manufacturer": None,
        "features": None,
        "graded": False,
        "grade": None,
        "grading_company": None,
        "cert_number": None
    }
    
    # Check if this is a PSA graded card first
    is_psa_card = _detect_psa_graded_card(text)
    if is_psa_card:
        return _extract_psa_card_details(text, player_name)
    
    # Continue with regular extraction for raw cards...

    # 1. Extract Year (prioritize recent years for current cards)
    year_matches = re.findall(r'\b(20[0-2]\d)\b', text)
    if year_matches:
        # Prefer the most recent year found
        details["year"] = max(year_matches)
    else:
        # Fallback to older years if no recent ones found
        year_match = re.search(r'\b(19[8-9]\d)\b', text)
        if year_match:
            details["year"] = year_match.group(0)

    # 2. Extract Card Number (various formats, avoid physical measurements)
    card_num_patterns = [
        r'(?:No\.|#|Card\s*#)\s*([A-Z0-9-]+)',  # Explicit card number indicators
        r'\b([A-Z]{1,3}-?\d{1,4}[A-Z]?)\b',     # Like RC-1, BDP-15, etc.
        r'CODE#([A-Z0-9]+)',                     # CODE# format
    ]
    
    for pattern in card_num_patterns:
        card_num_match = re.search(pattern, text, re.IGNORECASE)
        if card_num_match:
            potential_number = card_num_match.group(1)
            # Avoid physical measurements (height/weight patterns)
            if not re.match(r'^\d+["\']?\d*$', potential_number) and not re.search(r'[HW]:', text):
                details["card_number"] = potential_number
                break
    
    # If no explicit card number found, look for simple numbers but be more selective
    if not details["card_number"]:
        # Look for standalone numbers that aren't obviously measurements or years
        simple_numbers = re.findall(r'\b(\d{1,4})\b', text)
        for num in simple_numbers:
            num_int = int(num)
            # Skip if it looks like a year, weight, height, or other measurement
            if not (1900 <= num_int <= 2030 or num_int > 500 or 
                   any(measurement in text.upper() for measurement in ['H:', 'W:', 'HEIGHT', 'WEIGHT', 'LBS', 'KG'])):
                details["card_number"] = num
                break

    # 3. Extract Parallel/Rarity Information (CRITICAL for pricing)
    parallel_patterns = [
        r'\b(\d+/\d+)\b',  # Numbered parallels like 24/99, 1/1
        r'\b(SUPERFRACTOR|REFRACTOR|PRIZM|CHROME|GOLD|SILVER|BLACK|RED|BLUE|GREEN|ORANGE|PURPLE)\b',
        r'\b(AUTO|AUTOGRAPH|SIGNATURE|PATCH|JERSEY|RELIC|MEMORABILIA)\b',
        r'\b(RC|ROOKIE|RPA|ROOKIE PATCH AUTO)\b',
        r'\b(PRIZM|OPTIC|SELECT|MOSAIC)\b'
    ]
    
    parallel_found = []
    for pattern in parallel_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        parallel_found.extend(matches)
    
    if parallel_found:
        details["parallel"] = " ".join(set(parallel_found)).title()

    # 4. Extract Set/Edition (focus on actual product names)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Enhanced manufacturer keywords including smaller companies
    manufacturer_keywords = {
        'TOPPS': ['TOPPS', 'BOWMAN', 'CHROME'],
        'PANINI': ['PANINI', 'PRIZM', 'SELECT', 'MOSAIC', 'OPTIC', 'DONRUSS'],
        'UPPER DECK': ['UPPER DECK', 'UD'],
        'FLEER': ['FLEER'],
        'SCORE': ['SCORE'],
        'WILD CARD': ['WILD CARD'],
        'LEAF': ['LEAF'],
        'SAGE': ['SAGE'],
        'PRESS PASS': ['PRESS PASS']
    }
    
    potential_sets = []
    
    for line in lines:
        line_upper = line.upper()
        
        # Look for set names with manufacturer keywords
        for manufacturer, keywords in manufacturer_keywords.items():
            for keyword in keywords:
                if keyword in line_upper:
                    # Clean up the line
                    clean_line = line.strip()
                    clean_line = re.sub(r'^[@#&*]', '', clean_line)
                    clean_line = re.sub(r'Cards?$', '', clean_line, flags=re.IGNORECASE)
                    clean_line = re.sub(r'\d{4}', '', clean_line)  # Remove years
                    
                    if len(clean_line.strip()) > 3:
                        potential_sets.append(clean_line.strip())
                        if not details["manufacturer"]:
                            details["manufacturer"] = manufacturer
                    break
    
    # Also look for copyright lines that might indicate manufacturer
    copyright_patterns = [
        r'Copyright\s+\d{4}\s+([^,\.]+)',  # "Copyright 2024 Wild Card, Inc."
        r'©\s*\d{4}\s+([^,\.]+)',          # "© 2024 Wild Card"
    ]
    
    for pattern in copyright_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            copyright_company = match.group(1).strip()
            # Clean up common suffixes
            copyright_company = re.sub(r'\s+(Inc\.?|LLC\.?|Corp\.?)', '', copyright_company, flags=re.IGNORECASE)
            if len(copyright_company) > 3 and not details["set"]:
                potential_sets.append(copyright_company)
                if not details["manufacturer"]:
                    details["manufacturer"] = copyright_company.upper()
    
    # Select best set name (prefer shorter, cleaner names)
    if potential_sets:
        # Remove duplicates and sort by length
        unique_sets = list(set(potential_sets))
        unique_sets.sort(key=len)
        details["set"] = unique_sets[0].title()

    # 5. Extract Special Features
    feature_keywords = ['ROOKIE', 'RC', 'AUTO', 'AUTOGRAPH', 'PATCH', 'JERSEY', 'RELIC', 'MEMORABILIA', 'SERIAL', 'NUMBERED']
    features_found = []
    
    for keyword in feature_keywords:
        if keyword in text.upper():
            features_found.append(keyword)
    
    if features_found:
        details["features"] = ", ".join(set(features_found)).title()

    return details

def quick_graded_check(image_path):
    """
    Quick check to determine if a card is PSA graded before full OCR processing.
    This allows for faster, more targeted extraction.
    """
    try:
        # Use OAuth credentials from token.json
        import json
        from google.oauth2.credentials import Credentials
        
        if not os.path.exists('token.json'):
            return False
            
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        client = vision.ImageAnnotatorClient(credentials=creds)
        
        # Quick OCR scan for graded indicators
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            return False
            
        text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Use our quick detection function
        is_graded = _quick_graded_card_detection(text)
        
        if is_graded:
            print(f"🏆 Quick scan detected PSA graded card: {os.path.basename(image_path)}")
        
        return is_graded
        
    except Exception as e:
        print(f"Error in quick graded check for {image_path}: {e}")
        return False

def process_all_images_enhanced(image_paths):
    """
    Enhanced processing that uses filename for player names and OCR for card details.
    Includes quick graded card detection for optimized processing.
    """
    print("Step 2: Processing images with enhanced extraction...")

    # Use OAuth credentials from token.json
    try:
        import json
        from google.oauth2.credentials import Credentials
        
        if not os.path.exists('token.json'):
            print("Error: token.json not found. Please run authentication first.")
            return []
            
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        # Create credentials with Vision API scope
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        client = vision.ImageAnnotatorClient(credentials=creds)
    except Exception as e:
        print(f"Error initializing Google Vision client: {e}")
        return []

    processed_cards = []
    
    if not image_paths:
        print("No images found to process.")
        return []

    for image_path in tqdm(image_paths, desc="Processing images"):
        try:
            # Extract player name from filename first
            player_name = _extract_player_from_filename(image_path)
            
            if not player_name:
                print(f"\nWarning: Could not extract player name from {image_path}")
                continue
            
            # Get OCR text for set/year/parallel extraction
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            text = response.full_text_annotation.text if response.full_text_annotation else ""

            if response.error.message:
                raise Exception(f"{response.error.message}")

            # Enhanced extraction using filename + OCR
            card_details = _extract_card_details_enhanced(text, player_name)
            
            # Calculate confidence based on extracted fields
            required_fields = ['player', 'set', 'year']
            found_fields = [k for k in required_fields if card_details.get(k)]
            confidence = len(found_fields) / len(required_fields)
            
            # Add bonus confidence for parallel/special features
            if card_details.get('parallel') or card_details.get('features'):
                confidence = min(1.0, confidence + 0.2)

            result = {
                'image_path': image_path,
                'player': card_details.get('player'),
                'set': card_details.get('set'),
                'year': card_details.get('year'),
                'card_number': card_details.get('card_number'),
                'parallel': card_details.get('parallel'),
                'manufacturer': card_details.get('manufacturer'),
                'features': card_details.get('features'),
                'graded': card_details.get('graded', False),
                'grade': card_details.get('grade'),
                'grading_company': card_details.get('grading_company'),
                'cert_number': card_details.get('cert_number'),
                'extraction_confidence': round(confidence, 2),
                'extraction_method': 'filename + OCR',
                'full_ocr_text': text
            }
            processed_cards.append(result)

        except Exception as e:
            print(f"\nError processing {image_path}: {e}")
            # Still try to get player name from filename
            player_name = _extract_player_from_filename(image_path)
            processed_cards.append({
                'image_path': image_path, 
                'player': player_name, 
                'set': None, 
                'year': None, 
                'card_number': None,
                'parallel': None,
                'manufacturer': None,
                'features': None,
                'graded': False,
                'grade': None,
                'grading_company': None,
                'cert_number': None,
                'extraction_confidence': 0.3 if player_name else 0.0, 
                'extraction_method': 'filename only',
                'full_ocr_text': f"Error: {e}"
            })
    
    print("Enhanced image processing complete.")
    
    # Show summary
    with_player = sum(1 for card in processed_cards if card.get('player'))
    with_set = sum(1 for card in processed_cards if card.get('set'))
    with_year = sum(1 for card in processed_cards if card.get('year'))
    with_parallel = sum(1 for card in processed_cards if card.get('parallel'))
    graded_cards = sum(1 for card in processed_cards if card.get('graded'))
    
    print(f"📊 Extraction Summary:")
    print(f"  Players identified: {with_player}/{len(processed_cards)}")
    print(f"  Sets identified: {with_set}/{len(processed_cards)}")
    print(f"  Years identified: {with_year}/{len(processed_cards)}")
    print(f"  Parallels/Rarities: {with_parallel}/{len(processed_cards)}")
    print(f"  🏆 PSA Graded Cards: {graded_cards}/{len(processed_cards)}")
    
    return processed_cards

# Alias for backward compatibility
process_all_images = process_all_images_enhanced

if __name__ == '__main__':
    if os.path.exists('images'):
        test_image_paths = sorted([os.path.join('images', f) for f in os.listdir('images') if f.endswith('.jpg')])
        if test_image_paths:
            from dotenv import load_dotenv
            load_dotenv()
            
            results = process_all_images_enhanced(test_image_paths)
            print("\n--- Enhanced Processing Results ---")
            for card in results[:10]:  # Show first 10
                print(f"File: {os.path.basename(card['image_path'])}")
                print(f"  Player: {card['player']}")
                print(f"  Set: {card['set']}")
                print(f"  Year: {card['year']}")
                print(f"  Parallel: {card['parallel']}")
                print(f"  Confidence: {card['extraction_confidence']}")
                print("-" * 10)
        else:
            print("No JPGs found in 'images' folder for testing.")
    else:
        print("No 'images' directory found for testing.") 