import os
import re
import io
import json
from google.cloud import vision
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from tqdm import tqdm

def perform_ocr_on_image(image_path):
    """
    Perform OCR on a single image using Google Vision API.
    Returns the extracted text or None if failed.
    """
    try:
        # Initialize Vision client with same logic as other parts of the app
        creds = None
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        
        # Try OAuth token first
        if os.path.exists('token.json'):
            try:
                with open('token.json', 'r') as f:
                    token_data = json.load(f)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception:
                creds = None
        
        # Try service account
        if not creds and os.path.exists('credentials.json'):
            try:
                with open('credentials.json', 'r') as f:
                    secret_data = json.load(f)
                if secret_data.get('type') == 'service_account':
                    creds = service_account.Credentials.from_service_account_file(
                        'credentials.json', scopes=SCOPES
                    )
            except Exception:
                creds = None
        
        # Create client
        if creds:
            client = vision.ImageAnnotatorClient(credentials=creds)
        else:
            client = vision.ImageAnnotatorClient()
        
        # Read image file
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Vision API error: {response.error.message}")
            return None
        
        # Extract text
        if response.full_text_annotation:
            return response.full_text_annotation.text
        else:
            return ""
            
    except Exception as e:
        print(f"❌ OCR failed for {image_path}: {e}")
        return None

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
    
    # 1. Extract PSA Grade (most critical for pricing) - IMPROVED PATTERNS
    grade_patterns = [
        r'PSA\s+(\d+(?:\.\d+)?)\s+GEM\s+MINT',  # PSA 10 GEM MINT
        r'PSA\s+(\d+(?:\.\d+)?)',  # PSA 10, PSA 9.5
        r'GRADE\s*:?\s*(\d+(?:\.\d+)?)',  # GRADE: 10
        r'(\d+(?:\.\d+)?)\s+PSA(?:\s|$)',   # 10 PSA (reverse order)
        r'MINT\s+(\d+)(?!\d)',  # MINT 10 (but not MINT 125 etc)
        r'GEM\s+MINT\s+(\d+)(?!\d)'  # GEM MINT 10
    ]
    
    for pattern in grade_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            grade_candidate = match.group(1)
            # Validate grade is reasonable (1-10)
            if grade_candidate.isdigit() and 1 <= int(grade_candidate) <= 10:
                details["grade"] = grade_candidate
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
    
    # 4. Extract Set Name (PSA labels are very precise about sets) - IMPROVED PATTERNS
    set_patterns = [
        # Full set names with manufacturer (more specific patterns)
        r'(?:20\d{2}\s+)?(TOPPS\s+CHROME)(?:\s+(?:ROOKIE|RC|AUTO|GOLD|REFRACTOR))*',
        r'(?:20\d{2}\s+)?(BOWMAN\s+CHROME)(?:\s+(?:ROOKIE|RC|AUTO|PROSPECTS))*',
        r'(?:20\d{2}\s+)?(PANINI\s+PRIZM)(?:\s+(?:BASKETBALL|FOOTBALL|ROOKIE))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+SERIES)(?:\s+\d+)*',
        r'(?:20\d{2}\s+)?(BOWMAN\s+STERLING)(?:\s+(?:ROOKIE|RC|AUTO))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+FINEST)(?:\s+(?:ROOKIE|RC|AUTO))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+HERITAGE)(?:\s+(?:ROOKIE|RC))*',
        # Standalone premium set names
        r'\b(CHROME)(?:\s+(?:ROOKIE|RC|AUTO|CARD))*\b',
        r'\b(PRIZM)(?:\s+(?:BASKETBALL|FOOTBALL|ROOKIE))*\b',
        r'\b(SELECT|MOSAIC|OPTIC|STERLING|FINEST|HERITAGE)(?:\s+(?:ROOKIE|RC))*\b',
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
    
    # 5. Extract Card Number (PSA labels show card numbers clearly) - IMPROVED PATTERNS
    card_num_patterns = [
        r'#\s*([A-Z]*\d{1,4}[A-Z]?)(?:\s|$)',  # #150, #RC150, #150A (with word boundary)
        r'NO\.\s*([A-Z]*\d{1,4}[A-Z]?)(?:\s|$)',  # NO. 150, NO. RC150
        r'CARD\s*#?\s*([A-Z]*\d{1,4}[A-Z]?)(?:\s|$)',  # CARD #150
        r'\b([A-Z]{1,3}-?\d{1,4})(?:\s|$)'  # RC-1, BDP-15, etc.
    ]
    
    for pattern in card_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            card_num = match.group(1)
            # Avoid years and cert numbers and grades
            if not (len(card_num) >= 4 and card_num.isdigit() and 1900 <= int(card_num) <= 2030):
                # Skip if it matches our already found grade or cert
                if card_num != details.get("grade") and card_num != details.get("cert_number"):
                    details["card_number"] = card_num
                    print(f"  ✅ Card number found: {details['card_number']}")
                    break
    
    # 6. Extract Parallel/Insert Information (PSA is very specific) - IMPROVED ORDER
    parallel_patterns = [
        r'\b(\d+/\d+)\b',  # Numbered parallels like 24/99, 1/1
        r'\b(SUPERFRACTOR|GOLD\s+REFRACTOR|SILVER\s+REFRACTOR|BLACK\s+REFRACTOR|REFRACTOR)\b',
        r'\b(AUTO|AUTOGRAPH|SIGNATURE)\b',
        r'\b(PATCH|JERSEY|RELIC|MEMORABILIA)\b',
        r'\b(RC|ROOKIE|1ST\s+BOWMAN|ROOKIE\s+PATCH\s+AUTO|RPA)\b',
        r'\b(GOLD|SILVER|BLACK|RED|BLUE|GREEN|ORANGE|PURPLE)\s+(?:REFRACTOR|PARALLEL|PRIZM)\b',
        r'\b(CHROME|PRIZM)(?!\s+(?:CARD|ROOKIE\s+CARD))\b'  # Avoid "Chrome Card" or "Chrome Rookie Card"
    ]
    
    parallel_found = []
    for pattern in parallel_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        parallel_found.extend(matches)
    
    if parallel_found:
        # Remove duplicates and join in a logical order
        unique_parallels = []
        seen = set()
        # Define priority order for parallel terms
        priority_order = ['ROOKIE', 'RC', 'AUTO', 'AUTOGRAPH', 'PATCH', 'JERSEY', 'GOLD', 'SILVER', 'BLACK', 'RED', 'BLUE', 'GREEN', 'ORANGE', 'PURPLE', 'REFRACTOR', 'CHROME', 'PRIZM']
        
        # Add numbered parallels first (like 15/50)
        for item in parallel_found:
            if re.match(r'\d+/\d+', item) and item.lower() not in seen:
                unique_parallels.append(item)
                seen.add(item.lower())
        
        # Add other parallels in priority order
        for priority_item in priority_order:
            for item in parallel_found:
                if priority_item.lower() in item.lower() and item.lower() not in seen:
                    unique_parallels.append(item)
                    seen.add(item.lower())
        
        # Add any remaining items
        for item in parallel_found:
            if item.lower() not in seen:
                unique_parallels.append(item)
                seen.add(item.lower())
        
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
            # Avoid obvious physical measurements (but be less restrictive)
            if not re.match(r'^\d+["\']$', potential_number):  # Height like 6'2"
                details["card_number"] = potential_number
                break
    
    # If no explicit card number found, look for simple numbers but be more selective
    if not details["card_number"]:
        # Look for standalone numbers that aren't obviously measurements or years
        simple_numbers = re.findall(r'\b(\d{1,4})\b', text)
        for num in simple_numbers:
            num_int = int(num)
            # Skip if it looks like a year, or very high numbers suggesting measurements
            # But be more selective about what we consider measurements
            skip_this_number = False
            
            # Skip years
            if 1900 <= num_int <= 2030:
                skip_this_number = True
            
            # Skip very high numbers (likely measurements)
            elif num_int > 500:
                skip_this_number = True
            
            # Check if this number appears near measurement keywords (more context-aware)
            else:
                # Look for the number's context in the text
                num_pattern = rf'\b{num}\b'
                matches = list(re.finditer(num_pattern, text))
                for match in matches:
                    start, end = match.span()
                    # Get 20 characters before and after the number
                    context_start = max(0, start - 20)
                    context_end = min(len(text), end + 20)
                    context = text[context_start:context_end].upper()
                    
                    # Check if measurement keywords are near this specific occurrence
                    if any(keyword in context for keyword in ['HEIGHT', 'WEIGHT', 'LBS', 'KG', 'FT', 'IN']):
                        skip_this_number = True
                        break
            
            if not skip_this_number:
                details["card_number"] = num
                break

    # 3. Extract Parallel/Rarity Information (CRITICAL for pricing) - IMPROVED ORDER
    parallel_patterns = [
        r'\b(\d+/\d+)\b',  # Numbered parallels like 24/99, 1/1
        r'\b(SUPERFRACTOR|GOLD\s+REFRACTOR|SILVER\s+REFRACTOR|BLACK\s+REFRACTOR|REFRACTOR)\b',
        r'\b(AUTO|AUTOGRAPH|SIGNATURE)\b',
        r'\b(PATCH|JERSEY|RELIC|MEMORABILIA)\b',
        r'\b(RC|ROOKIE|RPA|ROOKIE\s+PATCH\s+AUTO)\b',
        r'\b(GOLD|SILVER|BLACK|RED|BLUE|GREEN|ORANGE|PURPLE)\s+(?:REFRACTOR|PARALLEL|PRIZM)\b',
        r'\b(PRIZM|OPTIC|SELECT|MOSAIC)(?!\s+(?:CARD|ROOKIE\s+CARD))\b'
    ]
    
    parallel_found = []
    for pattern in parallel_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        parallel_found.extend(matches)
    
    if parallel_found:
        # Remove duplicates and join in a logical order
        unique_parallels = []
        seen = set()
        # Define priority order for parallel terms  
        priority_order = ['ROOKIE', 'RC', 'AUTO', 'AUTOGRAPH', 'PATCH', 'JERSEY', 'GOLD', 'SILVER', 'BLACK', 'RED', 'BLUE', 'GREEN', 'ORANGE', 'PURPLE', 'REFRACTOR', 'CHROME', 'PRIZM', 'OPTIC', 'SELECT', 'MOSAIC']
        
        # Add numbered parallels first (like 15/50)
        for item in parallel_found:
            if re.match(r'\d+/\d+', item) and item.lower() not in seen:
                unique_parallels.append(item)
                seen.add(item.lower())
        
        # Add other parallels in priority order
        for priority_item in priority_order:
            for item in parallel_found:
                if priority_item.lower() in item.lower() and item.lower() not in seen:
                    unique_parallels.append(item)
                    seen.add(item.lower())
        
        # Add any remaining items
        for item in parallel_found:
            if item.lower() not in seen:
                unique_parallels.append(item)
                seen.add(item.lower())
        
        details["parallel"] = " ".join(unique_parallels).title()

    # 4. Extract Set/Edition (focus on actual product names) - IMPROVED PATTERNS
    # First try specific set patterns that are more precise
    set_patterns = [
        # Full set names with manufacturer (more specific patterns)
        r'(?:20\d{2}\s+)?(TOPPS\s+CHROME)(?:\s+(?:ROOKIE|RC|AUTO|GOLD|REFRACTOR|CARD))*',
        r'(?:20\d{2}\s+)?(BOWMAN\s+CHROME)(?:\s+(?:ROOKIE|RC|AUTO|PROSPECTS|CARD))*',
        r'(?:20\d{2}\s+)?(PANINI\s+PRIZM)(?:\s+(?:BASKETBALL|FOOTBALL|ROOKIE|CARD))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+SERIES)(?:\s+\d+)*',
        r'(?:20\d{2}\s+)?(BOWMAN\s+STERLING)(?:\s+(?:ROOKIE|RC|AUTO|CARD))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+FINEST)(?:\s+(?:ROOKIE|RC|AUTO|CARD))*',
        r'(?:20\d{2}\s+)?(TOPPS\s+HERITAGE)(?:\s+(?:ROOKIE|RC|CARD))*',
        # Standalone premium set names (without player names)
        r'\b(CHROME)(?:\s+(?:ROOKIE|RC|AUTO|CARD))*\b',
        r'\b(PRIZM)(?:\s+(?:BASKETBALL|FOOTBALL|ROOKIE|CARD))*\b',
        r'\b(SELECT|MOSAIC|OPTIC|STERLING|FINEST|HERITAGE)(?:\s+(?:ROOKIE|RC|CARD))*\b',
        # Simple manufacturer
        r'\b(TOPPS|PANINI|BOWMAN|DONRUSS|FLEER)(?!\s+(?:[A-Z]+\s+){2,})\b'
    ]
    
    # Try pattern-based extraction first
    for pattern in set_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            set_name = match.group(1).strip().title()
            if len(set_name) > 3 and set_name.upper() not in player_name.upper():
                details["set"] = set_name
                
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
    
    # If pattern-based didn't work, fall back to line-based approach
    if not details["set"]:
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
            
            # Skip lines that are mostly player names
            if player_name and len([word for word in player_name.upper().split() if word in line_upper]) >= 2:
                continue
            
            # Look for set names with manufacturer keywords
            for manufacturer, keywords in manufacturer_keywords.items():
                for keyword in keywords:
                    if keyword in line_upper:
                        # Clean up the line more aggressively
                        clean_line = line.strip()
                        clean_line = re.sub(r'^[@#&*]', '', clean_line)
                        clean_line = re.sub(r'Cards?$', '', clean_line, flags=re.IGNORECASE)
                        clean_line = re.sub(r'\d{4}', '', clean_line)  # Remove years
                        clean_line = re.sub(r'#\d+', '', clean_line)  # Remove card numbers
                        clean_line = re.sub(r'\b(RC|ROOKIE|AUTO|AUTOGRAPH|CARD)\b', '', clean_line, flags=re.IGNORECASE)
                        
                        # Remove player name components
                        if player_name:
                            for name_part in player_name.split():
                                if len(name_part) > 2:  # Only remove substantial name parts
                                    clean_line = re.sub(rf'\b{re.escape(name_part)}\b', '', clean_line, flags=re.IGNORECASE)
                        
                        clean_line = re.sub(r'\s+', ' ', clean_line).strip()  # Normalize spaces
                        
                        if len(clean_line) > 3 and clean_line.upper() not in ['RC', 'ROOKIE', 'AUTO', 'CARD']:
                            potential_sets.append(clean_line)
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
        
        creds = None

        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]

        # 1️⃣ Try OAuth token.json (interactive flow)
        if os.path.exists('token.json'):
            try:
                with open('token.json', 'r') as f:
                    token_data = json.load(f)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception:
                creds = None

        # 2️⃣ Try service-account key
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

        # 3️⃣ Fallback: default credentials (e.g., GOOGLE_APPLICATION_CREDENTIALS)
        if creds:
            client = vision.ImageAnnotatorClient(credentials=creds)
        else:
            client = vision.ImageAnnotatorClient()
        
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

def process_dual_side_card(front_image_path, back_image_path=None, player_name=None):
    """
    Process a card with front and optionally back images for comprehensive OCR.
    
    Front side typically contains: player name, team, parallel info
    Back side typically contains: year, card number, set info, stats
    
    Returns merged card details with confidence scoring.
    """
    print(f"🔍 Processing dual-side card...")
    
    # Extract player name from filename if not provided
    if not player_name:
        player_name = _extract_player_from_filename(front_image_path)
    
    front_details = {}
    back_details = {}
    
    # Process front side
    try:
        print(f"📄 Processing front: {os.path.basename(front_image_path)}")
        front_text = perform_ocr_on_image(front_image_path)
        if front_text:
            front_details = _extract_card_details_enhanced(front_text, player_name)
            front_details['ocr_source'] = 'front'
            print(f"   Front extracted: {len([k for k,v in front_details.items() if v])} fields")
        else:
            print("   ⚠️  No text from front side")
    except Exception as e:
        print(f"   ❌ Front side error: {e}")
    
    # Process back side if provided
    if back_image_path and os.path.exists(back_image_path):
        try:
            print(f"📄 Processing back: {os.path.basename(back_image_path)}")
            back_text = perform_ocr_on_image(back_image_path)
            if back_text:
                back_details = _extract_card_details_enhanced(back_text, player_name)
                back_details['ocr_source'] = 'back'
                print(f"   Back extracted: {len([k for k,v in back_details.items() if v])} fields")
            else:
                print("   ⚠️  No text from back side")
        except Exception as e:
            print(f"   ❌ Back side error: {e}")
    
    # Merge details with priority logic
    merged_details = _merge_dual_side_details(front_details, back_details, player_name)
    
    # Calculate confidence based on critical fields found
    confidence_score = _calculate_dual_side_confidence(merged_details)
    merged_details['confidence_score'] = confidence_score
    merged_details['dual_side'] = back_image_path is not None
    
    print(f"✅ Merged card details (confidence: {confidence_score:.1%})")
    return merged_details

def _merge_dual_side_details(front_details, back_details, player_name):
    """
    Merge front and back card details with smart priority logic.
    
    Priority rules:
    - Player name: filename > front > back
    - Year: back > front (usually clearer on back)
    - Card number: back > front (usually only on back)
    - Set: front > back (front typically has set name)
    - Parallel: front > back (foil/refractor visible on front)
    - Manufacturer: front > back
    - Features: combine both sides
    """
    merged = {}
    
    # Start with front details
    merged.update(front_details)
    
    # Priority overrides from back side
    priority_from_back = ['year', 'card_number', 'cert_number']
    for field in priority_from_back:
        if back_details.get(field) and not front_details.get(field):
            merged[field] = back_details[field]
        elif back_details.get(field) and len(str(back_details[field])) > len(str(front_details.get(field, ''))):
            # Use back if it has more detailed info
            merged[field] = back_details[field]
    
    # Combine features from both sides
    front_features = set((front_details.get('features') or '').split(', '))
    back_features = set((back_details.get('features') or '').split(', '))
    combined_features = front_features.union(back_features)
    combined_features.discard('')  # Remove empty strings
    if combined_features:
        merged['features'] = ', '.join(sorted(combined_features))
    
    # Use filename player name if provided
    if player_name:
        merged['player'] = player_name
    
    # Graded card detection from either side
    merged['graded'] = front_details.get('graded', False) or back_details.get('graded', False)
    if merged['graded']:
        # Use grading info from whichever side detected it
        grading_source = back_details if back_details.get('graded') else front_details
        for field in ['grade', 'grading_company', 'cert_number']:
            if grading_source.get(field):
                merged[field] = grading_source[field]
    
    # Add source tracking
    sources = []
    if front_details:
        sources.append('front')
    if back_details:
        sources.append('back')
    merged['ocr_sources'] = ', '.join(sources)
    
    return merged

def _calculate_dual_side_confidence(merged_details):
    """
    Calculate confidence score for dual-side processed card.
    
    Critical fields for trading card valuation:
    - Player name (weight: 0.3)
    - Year (weight: 0.25) 
    - Card number (weight: 0.25)
    - Set (weight: 0.2)
    
    Bonus points for additional details.
    """
    score = 0.0
    
    # Critical fields with weights
    critical_fields = {
        'player': 0.3,
        'year': 0.25,
        'card_number': 0.25,
        'set': 0.2
    }
    
    for field, weight in critical_fields.items():
        value = merged_details.get(field)
        if value and str(value).strip():
            # Extra points for detailed/realistic values
            if field == 'year' and str(value).isdigit() and 1980 <= int(value) <= 2030:
                score += weight * 1.1  # Bonus for valid year
            elif field == 'card_number' and len(str(value)) >= 1:
                score += weight * 1.0
            elif field == 'player' and len(str(value)) >= 3:
                score += weight * 1.0
            elif field == 'set' and len(str(value)) >= 3:
                score += weight * 1.0
            else:
                score += weight * 0.8  # Partial credit
    
    # Bonus points for additional details
    bonus_fields = ['parallel', 'manufacturer', 'features', 'graded']
    bonus_count = sum(1 for field in bonus_fields if merged_details.get(field))
    score += min(0.1, bonus_count * 0.025)  # Up to 10% bonus
    
    # Dual-side bonus
    if merged_details.get('dual_side'):
        score += 0.05  # 5% bonus for having both sides
    
    return min(1.0, score)  # Cap at 100%

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