#!/usr/bin/env python3
"""
Test script to verify all components before running full automation.
Tests Google Drive authentication, folder access, file download, and Vision API.
"""

import os
import sys
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_google_drive_auth():
    """Test 1: Authenticate with Google Drive using credentials.json"""
    print("=" * 60)
    print("TEST 1: Google Drive Authentication")
    print("=" * 60)
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        
        # Check if credentials.json exists
        if not os.path.exists('credentials.json'):
            print("❌ FAILED: credentials.json not found")
            print("   Please download credentials.json from Google Cloud Console")
            return None
        
        print("✅ credentials.json found")
        
        # Authenticate
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print("✅ Found existing token.json")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
            else:
                print("🔄 Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ Token saved to token.json")
        
        # Test API connection
        service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive API connection successful")
        return service
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None

def test_folder_access(service):
    """Test 2: Navigate to folder and list JPG files"""
    print("\n" + "=" * 60)
    print("TEST 2: Folder Access and File Listing")
    print("=" * 60)
    
    if not service:
        print("❌ SKIPPED: No Google Drive service available")
        return None, []
    
    try:
        folder_name = os.getenv("GDRIVE_FOLDER_NAME", "card-listings/heic.online (1)")
        print(f"🔍 Looking for folder: '{folder_name}'")
        
        # Find the folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        
        if not folders:
            print(f"❌ FAILED: Folder '{folder_name}' not found")
            print("   Available folders:")
            # List some folders for debugging
            all_folders = service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields='files(id, name)'
            ).execute()
            for folder in all_folders.get('files', [])[:10]:
                print(f"     - {folder['name']}")
            return None, []
        
        folder_id = folders[0]['id']
        print(f"✅ Found folder: '{folders[0]['name']}' (ID: {folder_id})")
        
        # List JPG files in the folder
        query = f"'{folder_id}' in parents and mimeType='image/jpeg' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, size)').execute()
        files = response.get('files', [])
        
        if not files:
            print("❌ FAILED: No JPG files found in the folder")
            return folder_id, []
        
        print(f"✅ Found {len(files)} JPG files:")
        for i, file in enumerate(files[:5]):  # Show first 5 files
            size_mb = int(file.get('size', 0)) / (1024 * 1024)
            print(f"     {i+1}. {file['name']} ({size_mb:.1f} MB)")
        
        if len(files) > 5:
            print(f"     ... and {len(files) - 5} more files")
        
        return folder_id, files
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None, []

def test_download_image(service, files):
    """Test 3: Download one test image"""
    print("\n" + "=" * 60)
    print("TEST 3: Download Test Image")
    print("=" * 60)
    
    if not service or not files:
        print("❌ SKIPPED: No service or files available")
        return None
    
    try:
        from googleapiclient.http import MediaIoBaseDownload
        
        # Create test directory
        test_dir = "test_images"
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        
        # Download first file
        test_file = files[0]
        file_id = test_file['id']
        file_name = f"test_image.jpg"
        local_path = os.path.join(test_dir, file_name)
        
        print(f"🔄 Downloading: {test_file['name']}")
        
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   Progress: {int(status.progress() * 100)}%")
        
        with open(local_path, 'wb') as f:
            f.write(fh.getvalue())
        
        file_size = os.path.getsize(local_path) / 1024
        print(f"✅ Downloaded successfully: {local_path} ({file_size:.1f} KB)")
        return local_path
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None

def test_vision_api(image_path, service=None):
    """Test 4: Run Google Vision API on test image"""
    print("\n" + "=" * 60)
    print("TEST 4: Google Vision API OCR")
    print("=" * 60)
    
    if not image_path:
        print("❌ SKIPPED: No test image available")
        return None
    
    try:
        from google.cloud import vision
        import json
        from google.oauth2.credentials import Credentials
        
        # Use OAuth credentials from token.json
        if not os.path.exists('token.json'):
            print("❌ FAILED: token.json not found")
            return None
            
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        # Create credentials with Vision API scope
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        print("✅ Using OAuth credentials from token.json")
        
        # Initialize Vision client with OAuth credentials
        client = vision.ImageAnnotatorClient(credentials=creds)
        print("✅ Vision API client initialized")
        
        # Read and process image
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            print(f"❌ FAILED: Vision API error: {response.error.message}")
            return None
        
        text = response.full_text_annotation.text
        
        if not text or not text.strip():
            print("⚠️  WARNING: No text detected in image")
            return ""
        
        print("✅ Text extraction successful!")
        print("\n" + "=" * 40)
        print("EXTRACTED TEXT:")
        print("=" * 40)
        print(text)
        print("=" * 40)
        
        # Basic analysis
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        print(f"\n📊 Analysis:")
        print(f"   - Total characters: {len(text)}")
        print(f"   - Lines of text: {len(lines)}")
        print(f"   - Words detected: {len(text.split())}")
        
        return text
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None

def main():
    """Run all tests in sequence"""
    print("🧪 TESTING TRADING CARDS AUTOMATION SETUP")
    print("=" * 60)
    
    # Test 1: Google Drive Authentication
    service = test_google_drive_auth()
    
    # Test 2: Folder Access
    folder_id, files = test_folder_access(service)
    
    # Test 3: Download Test Image
    image_path = test_download_image(service, files)
    
    # Test 4: Vision API
    extracted_text = test_vision_api(image_path)
    
    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    if service:
        print("✅ Google Drive Authentication: PASSED")
        tests_passed += 1
    else:
        print("❌ Google Drive Authentication: FAILED")
    
    if folder_id and files:
        print("✅ Folder Access & File Listing: PASSED")
        tests_passed += 1
    else:
        print("❌ Folder Access & File Listing: FAILED")
    
    if image_path:
        print("✅ Image Download: PASSED")
        tests_passed += 1
    else:
        print("❌ Image Download: FAILED")
    
    if extracted_text is not None:
        print("✅ Google Vision API: PASSED")
        tests_passed += 1
    else:
        print("❌ Google Vision API: FAILED")
    
    print(f"\n🎯 OVERALL RESULT: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Ready for full automation.")
        return True
    else:
        print("⚠️  SOME TESTS FAILED! Please fix issues before running full automation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 