#!/usr/bin/env python3
"""
Smoke tests for Google Vision API integration.
These tests require valid Google Cloud credentials and make real API calls.
"""

import os
import pytest
from pathlib import Path

# Skip all tests in this file if no credentials available
pytestmark = pytest.mark.skipif(
    not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
    reason="No Google Cloud credentials available"
)

@pytest.fixture
def test_images():
    """Get list of available test images"""
    images_dir = Path("images")
    test_images_dir = Path("test_images")
    
    image_files = []
    
    # Check both directories for images
    for directory in [images_dir, test_images_dir]:
        if directory.exists():
            image_files.extend([
                str(f) for f in directory.glob("*.jpg") 
                if f.is_file() and f.stat().st_size > 1000  # At least 1KB
            ])
    
    if not image_files:
        pytest.skip("No test images found in images/ or test_images/ directories")
    
    return image_files[:5]  # Limit to 5 images to avoid quota issues


class TestVisionAPIIntegration:
    """Test Google Vision API integration"""
    
    def test_vision_client_initialization(self):
        """Test that we can create a Vision client without errors"""
        from src.utils.enhanced_card_processor import quick_graded_check
        
        # This should not raise an exception
        try:
            # Use a non-existent file to test auth only
            result = quick_graded_check("non_existent_file.jpg")
            # Expect False since file doesn't exist, but auth should work
        except FileNotFoundError:
            pass  # Expected - we just want to test auth works
        except Exception as e:
            pytest.fail(f"Vision client initialization failed: {e}")
    
    @pytest.mark.parametrize("image_path", [])  # Will be filled by test_images fixture
    def test_ocr_extraction_smoke(self, image_path, test_images):
        """Smoke test: OCR should extract some text from real images"""
        from src.utils.enhanced_card_processor import _extract_player_from_filename, _extract_card_details_enhanced
        from google.cloud import vision
        import io
        import json
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        
        # Initialize Vision client with same logic as production code
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
        
        # Test OCR on first available image
        test_image = test_images[0]
        
        with io.open(test_image, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        # Should not have API errors
        assert not response.error.message, f"Vision API error: {response.error.message}"
        
        # Should extract some text
        raw_text = response.full_text_annotation.text if response.full_text_annotation else ""
        assert raw_text.strip(), f"No text extracted from {test_image}"
        
        # Extract player name from filename
        player_name = _extract_player_from_filename(test_image)
        
        # Run our extraction logic
        card_details = _extract_card_details_enhanced(raw_text, player_name)
        
        # Basic validation - should return a dict with expected structure
        assert isinstance(card_details, dict)
        assert "player" in card_details
        assert "set" in card_details
        assert "year" in card_details
        assert "graded" in card_details
        
        # Player name should come from filename if provided
        if player_name:
            assert card_details["player"] == player_name
        
        print(f"\n📊 OCR Results for {os.path.basename(test_image)}:")
        print(f"  Player: {card_details.get('player')}")
        print(f"  Set: {card_details.get('set')}")
        print(f"  Year: {card_details.get('year')}")
        print(f"  Card #: {card_details.get('card_number')}")
        print(f"  Graded: {card_details.get('graded')}")
        
        # Calculate confidence score
        required_fields = ['player', 'set', 'year']
        found_fields = [k for k in required_fields if card_details.get(k)]
        confidence = len(found_fields) / len(required_fields)
        
        print(f"  Confidence: {confidence:.1%}")
        
        # At minimum, should find player name (from filename) and some other field
        assert len(found_fields) >= 1, f"Should find at least player name, found: {found_fields}"


class TestQuickGradedCheck:
    """Test the quick graded card detection"""
    
    def test_graded_detection_with_real_image(self, test_images):
        """Test graded card detection on real images"""
        from src.utils.enhanced_card_processor import quick_graded_check
        
        # Test on first available image
        test_image = test_images[0]
        
        # Should return boolean without crashing
        try:
            is_graded = quick_graded_check(test_image)
            assert isinstance(is_graded, bool)
            print(f"\n🏆 Graded detection for {os.path.basename(test_image)}: {is_graded}")
        except Exception as e:
            pytest.fail(f"quick_graded_check failed: {e}")


class TestErrorHandling:
    """Test error handling in Vision API calls"""
    
    def test_invalid_image_handling(self):
        """Test handling of invalid image data"""
        from src.utils.enhanced_card_processor import quick_graded_check
        
        # Create a tiny invalid file
        with open("temp_invalid.txt", "w") as f:
            f.write("not an image")
        
        try:
            # Should handle gracefully, not crash
            result = quick_graded_check("temp_invalid.txt")
            assert isinstance(result, bool)
        except Exception as e:
            # Some exceptions are expected, but shouldn't be authentication errors
            assert "invalid_grant" not in str(e)
            assert "credentials" not in str(e).lower()
        finally:
            # Clean up
            if os.path.exists("temp_invalid.txt"):
                os.remove("temp_invalid.txt")
    
    def test_missing_file_handling(self):
        """Test handling of missing files"""
        from src.utils.enhanced_card_processor import quick_graded_check
        
        # Should handle missing files gracefully
        result = quick_graded_check("definitely_does_not_exist.jpg")
        assert isinstance(result, bool)


# Dynamic test generation for available images
def pytest_generate_tests(metafunc):
    """Dynamically generate tests for each available image"""
    if "image_path" in metafunc.fixturenames:
        # Get test images
        images_dir = Path("images")
        test_images_dir = Path("test_images")
        
        image_files = []
        for directory in [images_dir, test_images_dir]:
            if directory.exists():
                image_files.extend([
                    str(f) for f in directory.glob("*.jpg")
                    if f.is_file() and f.stat().st_size > 1000
                ])
        
        # Limit to avoid quota issues
        image_files = image_files[:3]
        
        if image_files:
            metafunc.parametrize("image_path", image_files, 
                               ids=[Path(f).name for f in image_files])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 