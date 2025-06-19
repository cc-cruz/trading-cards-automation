#!/usr/bin/env python3
"""
Pre-launch test runner for FlipHero.
Runs different test suites based on available resources.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success/failure"""
    print(f"\n🔄 {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def check_credentials():
    """Check if Google Cloud credentials are available"""
    return (
        os.path.exists('credentials.json') or 
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS') is not None
    )

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pytest
        import fastapi
        import google.cloud.vision
        import google.cloud.storage
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def main():
    """Run the appropriate test suites"""
    print("🃏 FlipHero Pre-Launch Test Suite")
    print("=" * 50)
    
    # Check prerequisites
    if not check_dependencies():
        print("❌ Dependencies not satisfied. Run: pip install -r requirements.txt")
        return False
    
    has_credentials = check_credentials()
    print(f"🔐 Google Cloud credentials: {'✅ Available' if has_credentials else '❌ Not found'}")
    
    results = []
    
    # 1. Unit tests (no external dependencies)
    results.append(run_command([
        sys.executable, "-m", "pytest", 
        "test_ocr_parser.py", 
        "-m", "not vision",
        "--tb=short"
    ], "Unit Tests (OCR Parser Logic)"))
    
    # 2. Vision API tests (if credentials available)
    if has_credentials:
        results.append(run_command([
            sys.executable, "-m", "pytest", 
            "test_vision_smoke.py", 
            "--tb=short", "-s"
        ], "Vision API Integration Tests"))
        
        results.append(run_command([
            sys.executable, "-m", "pytest", 
            "test_signed_upload.py", 
            "--tb=short", "-s"
        ], "Signed Upload Integration Tests"))
    else:
        print("⚠️  Skipping Vision API and Upload tests (no credentials)")
    
    # 3. Quick OCR test on real image
    if has_credentials and Path("test_images").exists():
        results.append(run_command([
            sys.executable, "test_single_card_ocr.py"
        ], "Single Card OCR Test"))
    
    # 4. Backend startup test
    print(f"\n🔄 Testing backend startup...")
    try:
        # Import the app to check for import errors
        from src.main import app
        print("✅ Backend Import - PASSED")
        results.append(True)
    except Exception as e:
        print(f"❌ Backend Import - FAILED: {e}")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"📈 Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Ready for user onboarding!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review before launch")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 