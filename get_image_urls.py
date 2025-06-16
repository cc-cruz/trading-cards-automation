#!/usr/bin/env python3

import sys
import os
import json
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def get_access_token():
    """Get a valid access token from existing OAuth credentials."""
    if not os.path.exists('token.json'):
        print("❌ token.json not found!")
        return None
    
    try:
        creds = Credentials.from_authorized_user_file('token.json')
        
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return creds.token
        
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None

def list_bucket_objects(bucket_name, folder_path="", access_token=None):
    """
    List objects in a GCS bucket using the REST API.
    
    Args:
        bucket_name (str): Name of the GCS bucket
        folder_path (str): Folder prefix to filter by
        access_token (str): OAuth access token
    
    Returns:
        list: List of object names
    """
    if not access_token:
        print("❌ No access token provided")
        return []
    
    # Build the API URL
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    params = {}
    if folder_path:
        params['prefix'] = folder_path
    
    try:
        print(f"🔍 Listing objects in bucket: {bucket_name}")
        if folder_path:
            print(f"📁 Folder: {folder_path}")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        print(f"📊 Found {len(items)} total objects")
        
        # Filter for image files
        image_objects = []
        for item in items:
            name = item['name']
            if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                image_objects.append(item)
        
        print(f"🖼️  Found {len(image_objects)} image files")
        return image_objects
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing bucket objects: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return []

def generate_image_urls(bucket_name, image_objects):
    """Generate public URLs for image objects."""
    image_urls = {}
    
    for obj in image_objects:
        filename = os.path.basename(obj['name'])
        public_url = f"https://storage.googleapis.com/{bucket_name}/{obj['name']}"
        image_urls[filename] = public_url
        print(f"  ✅ {filename}")
    
    return image_urls

def save_urls_to_file(image_urls, output_file="image_urls.json"):
    """Save the URL mapping to a JSON file for reference."""
    with open(output_file, 'w') as f:
        json.dump(image_urls, f, indent=2)
    print(f"💾 URLs saved to {output_file}")

def create_csv_mapping(image_urls, output_file="image_url_mapping.csv"):
    """Create a CSV file with filename to URL mapping for easy reference."""
    import csv
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Filename', 'Public URL'])
        
        for filename, url in sorted(image_urls.items()):
            writer.writerow([filename, url])
    
    print(f"📋 CSV mapping saved to {output_file}")

def main():
    """Get URLs from the specified GCS bucket and folder using REST API."""
    
    # Your bucket details
    BUCKET_NAME = "fliphero-cards-bucket"
    FOLDER_PATH = "heic.online (1)"
    
    print("=== Getting GCS Image URLs (REST API) ===")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Folder: {FOLDER_PATH}")
    print("🔐 Using OAuth access token...\n")
    
    # Get access token
    access_token = get_access_token()
    if not access_token:
        print("❌ Could not get access token")
        return
    
    # List bucket objects
    image_objects = list_bucket_objects(BUCKET_NAME, FOLDER_PATH, access_token)
    
    if not image_objects:
        print("❌ No images found in the specified bucket/folder")
        print("Please check:")
        print("  - Bucket name is correct")
        print("  - Folder path is correct")
        print("  - Images are actually uploaded")
        print("  - You have access to this bucket")
        return
    
    # Generate URLs
    print(f"\n📋 Generating URLs:")
    image_urls = generate_image_urls(BUCKET_NAME, image_objects)
    
    # Save URLs to files
    save_urls_to_file(image_urls)
    create_csv_mapping(image_urls)
    
    # Show some examples
    print(f"\n📋 Example URLs:")
    for i, (filename, url) in enumerate(list(image_urls.items())[:5]):
        print(f"  {filename}")
        print(f"    → {url}")
    
    if len(image_urls) > 5:
        print(f"  ... and {len(image_urls) - 5} more")
    
    print(f"\n✅ Success! Found {len(image_urls)} images")
    print(f"💾 URLs saved to image_urls.json and image_url_mapping.csv")
    print(f"🚀 Ready to run main pipeline with automatic image URLs!")
    
    # Test card matching
    print(f"\n📝 Testing card matching:")
    test_names = ["paul-skenes", "chourio", "skubal"]
    for name in test_names:
        matches = [f for f in image_urls.keys() if name.lower() in f.lower()]
        if matches:
            print(f"  {name}: Found {len(matches)} images - {matches}")
        else:
            print(f"  {name}: No matches found")

if __name__ == "__main__":
    main() 