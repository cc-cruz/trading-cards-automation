import os
import time
from typing import Dict, Optional
from urllib.parse import urlencode
import requests
from requests_oauthlib import OAuth2Session

from src.database import get_db

EBAY_OAUTH_AUTHORIZE_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_OAUTH_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"

class EbayService:
    """Simple eBay REST wrapper supporting OAuth and listing creation (draft)."""

    def __init__(self, db=None):
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("EBAY_REDIRECT_URI", "https://localhost/ebay/callback")
        self.scope = EBAY_SCOPE.split()

        if not self.client_id or not self.client_secret:
            raise RuntimeError("EBAY credentials not configured")

        self.session: Optional[OAuth2Session] = None

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------
    def get_authorization_url(self, state: str) -> str:
        ebay = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope)
        auth_url, _ = ebay.authorization_url(EBAY_OAUTH_AUTHORIZE_URL, state=state)
        return auth_url

    def fetch_token(self, authorization_response: str) -> Dict:
        ebay = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope)
        token = ebay.fetch_token(
            EBAY_OAUTH_TOKEN_URL,
            authorization_response=authorization_response,
            client_secret=self.client_secret,
        )
        return token

    # ------------------------------------------------------------------
    # Listing (draft) creation
    # ------------------------------------------------------------------
    def create_listing(self, access_token: str, *, title: str, description: str, price: float, quantity: int = 1, sku: Optional[str] = None) -> Dict:
        """Creates a draft inventory item + offer via Inventory API.
        NOTE: This is a simplified flow; in production we need proper inventory + offer publish steps.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        inventory_item_key = sku or f"CARD-{int(time.time())}"
        inventory_url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{inventory_item_key}"
        inventory_payload = {
            "availability": {
                "shipToLocationAvailability": {"quantity": quantity}
            },
            "condition": "NEW",
            "product": {
                "title": title,
                "description": description,
            },
        }

        r1 = requests.put(inventory_url, json=inventory_payload, headers=headers)
        r1.raise_for_status()

        # Create offer
        offer_url = "https://api.ebay.com/sell/inventory/v1/offer"
        offer_payload = {
            "sku": inventory_item_key,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "availableQuantity": quantity,
            "listingDescription": description,
            "pricingSummary": {"price": {"value": price, "currency": "USD"}},
        }
        r2 = requests.post(offer_url, json=offer_payload, headers=headers)
        r2.raise_for_status()
        return r2.json()


def get_ebay_service(db=None) -> EbayService:
    """Dependency function to get EbayService instance"""
    if db is None:
        db = next(get_db())
    return EbayService(db) 