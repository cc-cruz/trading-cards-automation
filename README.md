# Trading Cards Automation

Automated eBay listing generator for trading cards using Google Drive and Vision API.

## Project Structure

```
trading-cards-automation/
├── credentials.json          ← Google APIs (REQUIRED)
├── .env                      ← Environment variables (REQUIRED)
├── requirements.txt          ← Python dependencies
├── main.py                   ← Main orchestration script
└── src/
    ├── drive_downloader.py   ← Google Drive image downloader
    ├── card_processor.py     ← OCR and card data extraction
    └── price_finder.py       ← eBay price research
```

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env file
Create a `.env` file in the root directory with:
```
GDRIVE_FOLDER_NAME="card-listings/heic.online (1)"
GOOGLE_APPLICATION_CREDENTIALS="credentials.json"
```

### 3. Google APIs Setup

#### Google Drive API:
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/library/drive.googleapis.com)
2. Enable the Google Drive API
3. Create OAuth2 credentials (Desktop app)
4. Download and rename to `credentials.json`

#### Google Vision API:
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/library/vision.googleapis.com)
2. Enable the Cloud Vision API
3. Create a Service Account with Vision AI User role
4. Download the JSON key and save as `credentials.json` (or update .env path)

## Usage

Run the complete pipeline:
```bash
python main.py
```

Or test individual components:
```bash
python src/drive_downloader.py
python src/card_processor.py
python src/price_finder.py
```

## Output

The script generates `ebay_listings.csv` with columns:
- Title, Sport, Purchase Price, Purchase Date
- Player, Set, Year, Card Manufacturer, Card Number
- Graded (Y/N), Card Condition, Professional Grader, Grade
- Certification Number, Parallel, Features

## Success Criteria

- 20+ cards successfully identified (80% success rate)
- Pricing within ±25% of market value
- Complete CSV ready for eBay bulk upload
- Execution time under 30 minutes 