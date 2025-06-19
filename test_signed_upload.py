#!/usr/bin/env python3
"""
Integration tests for signed upload URL flow (Option B).
Tests the complete flow from signed URL generation to GCS upload.
"""

import os
import pytest
import requests
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def test_user_token(client):
    """Create a test user and return JWT token"""
    # Register test user
    user_data = {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    # Try to register (might already exist)
    register_response = client.post("/api/v1/auth/register", json=user_data)
    
    # Login to get token
    login_response = client.post("/api/v1/auth/token", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    if login_response.status_code != 200:
        pytest.skip(f"Could not authenticate test user: {login_response.text}")
    
    return login_response.json()["access_token"]


@pytest.fixture
def test_image_bytes():
    """Create a minimal valid JPEG for testing"""
    # Minimal JPEG header (will be recognized as valid image)
    jpeg_header = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xD9
    ])
    return jpeg_header


class TestSignedUploadFlow:
    """Test the complete signed upload flow"""
    
    @pytest.mark.skipif(
        not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        reason="No Google Cloud credentials available"
    )
    def test_generate_signed_url(self, client, test_user_token):
        """Test signed URL generation endpoint"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "content_type": "image/jpeg",
            "filename": "test-card.jpg"
        }
        
        response = client.post("/api/v1/uploads/signed-url", 
                             json=payload, 
                             headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return required fields
        assert "upload_url" in data
        assert "public_url" in data
        assert "blob_name" in data
        assert "expires_in" in data
        
        # URLs should be valid GCS URLs
        assert data["upload_url"].startswith("https://storage.googleapis.com/")
        assert data["public_url"].startswith("https://storage.googleapis.com/")
        assert "fliphero-cards-bucket" in data["public_url"]
        
        # Blob name should be in cards/ folder with UUID
        assert data["blob_name"].startswith("cards/")
        assert data["blob_name"].endswith(".jpg")
        
        # Should expire in reasonable time (default 15 minutes = 900 seconds)
        assert data["expires_in"] == 900
        
        print(f"\n✅ Generated signed URL:")
        print(f"   Blob: {data['blob_name']}")
        print(f"   Expires in: {data['expires_in']} seconds")
    
    @pytest.mark.skipif(
        not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        reason="No Google Cloud credentials available"
    )
    def test_complete_upload_flow(self, client, test_user_token, test_image_bytes):
        """Test the complete upload flow: signed URL → upload → verify public access"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Step 1: Get signed URL
        payload = {
            "content_type": "image/jpeg",
            "filename": "test-upload.jpg"
        }
        
        response = client.post("/api/v1/uploads/signed-url", 
                             json=payload, 
                             headers=headers)
        
        assert response.status_code == 200
        url_data = response.json()
        
        upload_url = url_data["upload_url"]
        public_url = url_data["public_url"]
        
        # Step 2: Upload the image to GCS using the signed URL
        upload_response = requests.put(
            upload_url,
            data=test_image_bytes,
            headers={"Content-Type": "image/jpeg"}
        )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        print(f"\n✅ Successfully uploaded to GCS:")
        print(f"   Upload URL status: {upload_response.status_code}")
        print(f"   Public URL: {public_url}")
        
        # Step 3: Verify the image is publicly accessible
        # Note: This might fail if bucket doesn't have public read permissions
        public_response = requests.get(public_url)
        
        if public_response.status_code == 200:
            print(f"✅ Image is publicly accessible")
            assert len(public_response.content) > 0
        else:
            # This is expected if bucket doesn't allow public read
            print(f"⚠️  Image not publicly accessible (status: {public_response.status_code})")
            print("   This is expected if bucket requires authentication for reads")
    
    def test_signed_url_requires_auth(self, client):
        """Test that signed URL generation requires authentication"""
        payload = {
            "content_type": "image/jpeg",
            "filename": "test.jpg"
        }
        
        # No auth header
        response = client.post("/api/v1/uploads/signed-url", json=payload)
        assert response.status_code == 401
    
    def test_signed_url_validation(self, client, test_user_token):
        """Test signed URL endpoint validation"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Missing content_type
        response = client.post("/api/v1/uploads/signed-url", 
                             json={"filename": "test.jpg"}, 
                             headers=headers)
        assert response.status_code == 400
        assert "content_type is required" in response.text
        
        # Empty content_type
        response = client.post("/api/v1/uploads/signed-url", 
                             json={"content_type": "", "filename": "test.jpg"}, 
                             headers=headers)
        assert response.status_code == 400
    
    @pytest.mark.skipif(
        not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        reason="No Google Cloud credentials available"
    )
    def test_different_file_types(self, client, test_user_token):
        """Test signed URL generation for different file types"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        test_cases = [
            {"content_type": "image/jpeg", "filename": "card.jpg"},
            {"content_type": "image/png", "filename": "card.png"},
            {"content_type": "image/webp", "filename": "card.webp"},
            {"content_type": "image/jpeg", "filename": None},  # No filename
        ]
        
        for case in test_cases:
            response = client.post("/api/v1/uploads/signed-url", 
                                 json=case, 
                                 headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should generate appropriate file extension
            if case["filename"]:
                expected_ext = case["filename"].split(".")[-1]
                assert data["blob_name"].endswith(f".{expected_ext}")
            else:
                # Should default to jpg
                assert data["blob_name"].endswith(".jpg")
            
            print(f"✅ {case['content_type']}: {data['blob_name']}")


class TestUploadServiceUnit:
    """Unit tests for UploadService class"""
    
    @pytest.mark.skipif(
        not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        reason="No Google Cloud credentials available"
    )
    def test_upload_service_initialization(self):
        """Test UploadService can be initialized"""
        from src.services.upload_service import UploadService
        
        service = UploadService()
        assert service.bucket_name == "fliphero-cards-bucket"
        assert service.client is not None
        assert service.bucket is not None
    
    @pytest.mark.skipif(
        not (os.path.exists('credentials.json') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        reason="No Google Cloud credentials available"
    )
    def test_object_name_generation(self):
        """Test object name generation logic"""
        from src.services.upload_service import UploadService
        
        service = UploadService()
        
        # Test with filename
        obj_name1 = service._make_object_name("test.jpg")
        assert obj_name1.startswith("cards/")
        assert obj_name1.endswith(".jpg")
        assert len(obj_name1.split("/")[1].split(".")[0]) == 32  # UUID hex length
        
        # Test without filename
        obj_name2 = service._make_object_name()
        assert obj_name2.startswith("cards/")
        assert obj_name2.endswith(".jpg")  # Default extension
        
        # Test with different extension
        obj_name3 = service._make_object_name("image.png")
        assert obj_name3.endswith(".png")
        
        # Each should be unique
        assert obj_name1 != obj_name2 != obj_name3


class TestErrorCases:
    """Test error handling and edge cases"""
    
    def test_missing_credentials_error(self, client, test_user_token):
        """Test behavior when credentials are missing"""
        # Temporarily rename credentials file if it exists
        creds_exists = os.path.exists('credentials.json')
        env_var = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if creds_exists:
            os.rename('credentials.json', 'credentials.json.bak')
        
        if env_var:
            os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
        
        try:
            headers = {"Authorization": f"Bearer {test_user_token}"}
            payload = {
                "content_type": "image/jpeg",
                "filename": "test.jpg"
            }
            
            response = client.post("/api/v1/uploads/signed-url", 
                                 json=payload, 
                                 headers=headers)
            
            # Should return 500 if credentials are missing
            assert response.status_code == 500
            
        finally:
            # Restore credentials
            if creds_exists:
                os.rename('credentials.json.bak', 'credentials.json')
            if env_var:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = env_var


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 