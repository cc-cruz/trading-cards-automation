import os
import io
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/cloud-platform'
]
DRIVE_FOLDER_NAME = os.getenv("GDRIVE_FOLDER_NAME")
OUTPUT_DIR = "images"

def authenticate_google_drive():
    """Handles Google Drive API authentication."""
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

def download_from_drive():
    """
    Downloads all JPG files from a specified Google Drive folder.
    - Authenticates with Google Drive API.
    - Finds the specified folder.
    - Downloads all JPG files into a local 'images' directory.
    - Saves them as numbered files (001.jpg, 002.jpg, etc.).
    - Returns a list of local file paths.
    """
    print("Step 1: Downloading images from Google Drive...")
    creds = authenticate_google_drive()
    if not creds:
        return []

    try:
        service = build('drive', 'v3', credentials=creds)

        # Find the folder
        query = f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])

        if not folders:
            print(f"Error: Google Drive folder '{DRIVE_FOLDER_NAME}' not found.")
            return []
        
        folder_id = folders[0]['id']
        print(f"Found folder: '{folders[0]['name']}' (ID: {folder_id})")

        # List JPG files in the folder
        query = f"'{folder_id}' in parents and mimeType='image/jpeg' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if not files:
            print("No JPG files found in the specified folder.")
            return []

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        print(f"Found {len(files)} JPG files. Starting download...")
        downloaded_files = []
        file_counter = 1

        for item in tqdm(files, desc="Downloading images"):
            file_id = item['id']
            file_name = f"{str(file_counter).zfill(3)}.jpg"
            local_path = os.path.join(OUTPUT_DIR, file_name)
            
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()

            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            downloaded_files.append(local_path)
            file_counter += 1

        print(f"Image download complete. {len(downloaded_files)} files saved to '{OUTPUT_DIR}' directory.")
        return downloaded_files

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

if __name__ == '__main__':
    # For testing the module directly
    downloaded_image_paths = download_from_drive()
    if downloaded_image_paths:
        print("\nDownloaded files:")
        for path in downloaded_image_paths:
            print(path) 