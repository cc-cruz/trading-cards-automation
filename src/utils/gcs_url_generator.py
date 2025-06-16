import os
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import json

# Same scopes as used in drive_downloader.py
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/cloud-platform'
]

def authenticate_google_services():
    """
    Handles Google API authentication using the same method as drive_downloader.py
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: `credentials.json` not found.")
                print("Please follow the setup instructions to download it from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_authenticated_storage_client():
    """
    Get an authenticated Google Cloud Storage client using OAuth credentials.
    """
    creds = authenticate_google_services()
    if not creds:
        return None
    
    try:
        # Create storage client with OAuth credentials
        # We need to extract the project ID from the credentials or use a default
        client = storage.Client(credentials=creds)
        return client
        
    except Exception as e:
        print(f"❌ Error creating storage client: {e}")
        return None

def get_gcs_image_urls(bucket_name, folder_path=""):
    """
    Get direct public URLs for all images in a Google Cloud Storage bucket/folder.
    Uses OAuth credentials consistent with other modules.
    
    Args:
        bucket_name (str): Name of your GCS bucket
        folder_path (str): Path to folder within bucket (optional)
    
    Returns:
        dict: Mapping of image filenames to their public URLs
    """
    print(f"🔍 Getting image URLs from GCS bucket: {bucket_name}")
    print("🔐 Using OAuth credentials...")
    
    # Get authenticated client
    client = get_authenticated_storage_client()
    if not client:
        return {}
    
    try:
        bucket = client.bucket(bucket_name)
        
        # List all blobs in the bucket/folder
        if folder_path:
            blobs = bucket.list_blobs(prefix=folder_path)
            print(f"📁 Looking in folder: {folder_path}")
        else:
            blobs = bucket.list_blobs()
            print("📁 Looking in root of bucket")
        
        image_urls = {}
        image_count = 0
        
        for blob in blobs:
            # Only process image files
            if blob.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # Get the filename without path
                filename = os.path.basename(blob.name)
                
                # Generate public URL
                # Format: https://storage.googleapis.com/bucket-name/path/to/file
                public_url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
                
                image_urls[filename] = public_url
                image_count += 1
                
                print(f"  ✅ {filename}")
        
        print(f"\n📊 Found {image_count} images in bucket")
        return image_urls
        
    except Exception as e:
        print(f"❌ Error accessing bucket: {e}")
        print("Please check:")
        print("  - Bucket name is correct")
        print("  - You have access to this bucket")
        print("  - Bucket exists and contains images")
        return {}

def save_urls_to_file(image_urls, output_file="image_urls.json"):
    """Save the URL mapping to a JSON file for reference."""
    with open(output_file, 'w') as f:
        json.dump(image_urls, f, indent=2)
    print(f"💾 URLs saved to {output_file}")

def create_csv_mapping(image_urls, output_file="image_url_mapping.csv"):
    """
    Create a CSV file with filename to URL mapping for easy reference.
    """
    import csv
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Filename', 'Public URL'])
        
        for filename, url in sorted(image_urls.items()):
            writer.writerow([filename, url])
    
    print(f"📋 CSV mapping saved to {output_file}")

def get_urls_for_card_images(image_urls, card_name):
    """
    Get URLs for a specific card (front and back images).
    
    Args:
        image_urls (dict): Dictionary of filename -> URL mappings
        card_name (str): Base name of the card (e.g., "paul-skenes")
    
    Returns:
        list: List of URLs for this card
    """
    card_urls = []
    
    # Look for front and back images
    for filename, url in image_urls.items():
        if card_name.lower() in filename.lower():
            card_urls.append(url)
    
    return card_urls

def main():
    """
    Main function to get all image URLs from your GCS bucket.
    Uses the same OAuth credentials as your Drive/Vision API setup.
    """
    
    print("=== Google Cloud Storage URL Generator ===")
    print("🔐 Using OAuth credentials (same as Drive/Vision API)\n")
    
    # Get bucket details from user
    print("Please provide your Google Cloud Storage details:")
    bucket_name = input("Bucket name: ").strip()
    
    if not bucket_name:
        print("❌ Bucket name is required!")
        return
    
    folder_path = input("Folder path (press Enter if images are in root): ").strip()
    
    # Remove trailing slash if present
    if folder_path.endswith('/'):
        folder_path = folder_path[:-1]
    
    try:
        # Get all image URLs
        image_urls = get_gcs_image_urls(bucket_name, folder_path)
        
        if not image_urls:
            print("❌ No images found in the specified bucket/folder")
            print("Please check:")
            print("  - Bucket name is correct")
            print("  - Folder path is correct") 
            print("  - Images are actually uploaded")
            print("  - You have access to this bucket with your OAuth credentials")
            return
        
        # Save URLs to files
        save_urls_to_file(image_urls)
        create_csv_mapping(image_urls)
        
        # Show some examples
        print(f"\n📋 Example URLs:")
        for i, (filename, url) in enumerate(list(image_urls.items())[:3]):
            print(f"  {filename}: {url}")
        
        if len(image_urls) > 3:
            print(f"  ... and {len(image_urls) - 3} more")
        
        print(f"\n✅ All URLs ready for eBay CSV!")
        print(f"💡 You can now run your main pipeline - it will automatically include these image URLs")
        print(f"💡 For multiple images per listing, URLs are automatically combined with | character")
        
        # Example of how to use for a specific card
        print(f"\n📝 Example for Paul Skenes card:")
        paul_urls = get_urls_for_card_images(image_urls, "paul-skenes")
        if paul_urls:
            combined_urls = "|".join(paul_urls)
            print(f"  Found {len(paul_urls)} images")
            print(f"  Combined URL string: {combined_urls}")
        else:
            print("  No Paul Skenes images found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Your OAuth credentials should work for Cloud Storage")
        print("  2. Make sure the bucket name is correct")
        print("  3. Verify you have access to the bucket")
        print("  4. Try re-authenticating if needed")

if __name__ == "__main__":
    main() 