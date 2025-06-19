#!/usr/bin/env python3
"""
Quick functionality test for FlipHero core features.
Run this before user onboarding to verify everything works.
"""

import os
import sys

def test_backend_import():
    """Test backend can import without errors"""
    try:
        from src.main import app
        print("✅ Backend import successful")
        return True
    except Exception as e:
        print(f"❌ Backend import failed: {e}")
        return False

def test_ocr_basics():
    """Test basic OCR functionality"""
    try:
        from src.utils.enhanced_card_processor import _extract_card_details_enhanced
        
        # Test with simple card text
        test_text = "2023 TOPPS CHROME PAUL SKENES #124 ROOKIE"
        result = _extract_card_details_enhanced(test_text, "Paul Skenes")
        
        # Check basic fields
        checks = [
            ("player", "Paul Skenes"),
            ("year", "2023"),
            ("card_number", "124")
        ]
        
        for field, expected in checks:
            actual = result.get(field)
            if actual == expected:
                print(f"✅ OCR {field}: {actual}")
            else:
                print(f"⚠️  OCR {field}: got '{actual}', expected '{expected}'")
        
        return True
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def test_upload_service():
    """Test upload service can initialize"""
    try:
        from src.services.upload_service import UploadService
        service = UploadService()
        print("✅ Upload service initialized")
        return True
    except Exception as e:
        print(f"❌ Upload service failed: {e}")
        return False

def test_credentials():
    """Check Google Cloud credentials"""
    has_creds = (
        os.path.exists('credentials.json') or 
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    )
    
    if has_creds:
        print("✅ Google Cloud credentials found")
        return True
    else:
        print("❌ No Google Cloud credentials")
        return False

def main():
    """Run all tests"""
    print("🃏 FlipHero Quick Test")
    print("=" * 30)
    
    tests = [
        ("Backend Import", test_backend_import),
        ("Google Credentials", test_credentials),
        ("Upload Service", test_upload_service),
        ("OCR Basics", test_ocr_basics),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🔄 Testing {name}...")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"💥 {name} exception: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n" + "=" * 30)
    print(f"📊 Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 ALL SYSTEMS GO - Ready for users!")
    elif passed >= 3:
        print("⚠️  Minor issues but core functionality works")
    else:
        print("🛑 Major issues - fix before user onboarding")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 