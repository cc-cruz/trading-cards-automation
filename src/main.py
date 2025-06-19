from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta

from .database import get_db, engine, Base
from .services.auth_service import AuthService, get_auth_service, oauth2_scheme
from .services.card_service import CardService, get_card_service
from .services.price_service import PriceService, get_price_service
from .services.analytics_service import AnalyticsService, get_analytics_service
from .services.card_database_service import HybridPricingService, get_hybrid_pricing_service, CardDatabaseService, get_card_database_service
from .services.ebay_service import EbayService, get_ebay_service
from .services.billing_service import BillingService, get_billing_service, STRIPE_PRICES
from .services.upload_service import UploadService, get_upload_service
from .schemas.auth import Token, UserCreate, GoogleOAuthRequest, AppleOAuthRequest, UserResponse, User
from .schemas.card import CardCreate, CardUpdate, Card as CardSchema
from .models.user import User
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FlipHero API",
    description="API for the FlipHero trading card platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded images
app.mount("/images", StaticFiles(directory="images"), name="images")

# Auth routes
@app.post("/api/v1/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type.value if hasattr(user.user_type, 'value') else str(user.user_type),
        created_at=user.created_at.isoformat()
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_response}

@app.post("/api/v1/auth/register", response_model=Token)
async def register(
    user: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    db_user = auth_service.create_user(user)
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        full_name=db_user.full_name,
        user_type=db_user.user_type.value if hasattr(db_user.user_type, 'value') else str(db_user.user_type),
        created_at=db_user.created_at.isoformat()
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_response}

@app.post("/api/v1/auth/google", response_model=Token)
async def google_oauth(
    request: GoogleOAuthRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user with Google OAuth token"""
    try:
        user = await auth_service.authenticate_google_user(request.token)
        
        access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            user_type=user.user_type.value if hasattr(user.user_type, 'value') else str(user.user_type),
            created_at=user.created_at.isoformat()
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": user_response}
        
    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed"
        )

@app.post("/api/v1/auth/apple", response_model=Token)
async def apple_oauth(
    request: AppleOAuthRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user with Apple ID token"""
    try:
        user = await auth_service.authenticate_apple_user(
            request.id_token, 
            request.user
        )
        
        access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            user_type=user.user_type.value if hasattr(user.user_type, 'value') else str(user.user_type),
            created_at=user.created_at.isoformat()
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": user_response}
        
    except Exception as e:
        logger.error(f"Apple OAuth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple authentication failed"
        )

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_auth_service().get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        user_type=current_user.user_type.value if hasattr(current_user.user_type, 'value') else str(current_user.user_type),
        created_at=current_user.created_at.isoformat()
    )

# Card routes

@app.get("/api/v1/cards/recent")
async def get_recent_cards(
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service),
    limit: int = 6
):
    """Get recently added cards for the current user"""
    recent_cards = card_service.get_recent_cards(current_user.id, limit)
    return recent_cards

@app.post("/api/v1/cards/upload")
async def upload_card_image(
    file: UploadFile = File(...),
    collection_id: str = Form(...),
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    """Upload and process a card image with OCR and price research"""
    try:
        # Process the uploaded image
        result = await card_service.process_card_image(file, collection_id, current_user.id)
        return {
            "status": "success",
            "card_data": result["card_data"],
            "price_data": result["price_data"],
            "card_id": result["card_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cards", response_model=CardSchema)
async def create_card(
    card: CardCreate,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    return await card_service.process_card_image(card.image, card.collection_id)

@app.get("/api/v1/cards/{card_id}", response_model=CardSchema)
async def get_card(
    card_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@app.get("/api/v1/collections/{collection_id}/cards", response_model=list[CardSchema])
async def get_collection_cards(
    collection_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    return card_service.get_collection_cards(collection_id)

@app.put("/api/v1/cards/{card_id}", response_model=CardSchema)
async def update_card(
    card_id: str,
    card_update: CardUpdate,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    card = card_service.update_card(card_id, card_update)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@app.delete("/api/v1/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    success = card_service.delete_card(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "success"}

# Collection routes
@app.get("/api/v1/collections")
async def get_collections(
    current_user: User = Depends(get_auth_service().get_current_user),
    db: Session = Depends(get_db)
):
    """Get all collections for the current user with cards data"""
    from .models.collection import Collection
    from .models.card import Card
    
    collections = db.query(Collection).filter(Collection.user_id == current_user.id).all()
    
    result = []
    for c in collections:
        # Get cards for this collection
        cards = db.query(Card).filter(Card.collection_id == c.id).all()
        
        collection_data = {
            "id": c.id, 
            "name": c.name, 
            "description": c.description,
            "cards": [
                {
                    "id": card.id,
                    "player_name": card.player_name,
                    "set_name": card.set_name,
                    "year": card.year,
                    "card_number": card.card_number,
                    "price_data": card.price_data
                }
                for card in cards
            ]
        }
        result.append(collection_data)
    
    return result

@app.post("/api/v1/collections")
async def create_collection(
    collection_data: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new collection"""
    from .models.collection import Collection
    collection = Collection(
        user_id=current_user.id,
        name=collection_data.get("name", "My Collection"),
        description=collection_data.get("description", "")
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return {"id": collection.id, "name": collection.name, "description": collection.description}

# Collection stats routes
@app.get("/api/v1/collections/stats")
async def get_collection_stats(
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    """Get collection statistics for the current user"""
    stats = card_service.get_user_collection_stats(current_user.id)
    return stats

@app.post("/api/v1/collections/{collection_id}/export")
async def export_collection(
    collection_id: str,
    export_data: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service),
    db: Session = Depends(get_db)
):
    """Export collection as CSV for eBay bulk upload"""
    from fastapi.responses import StreamingResponse
    import pandas as pd
    import io
    # Import models for query
    from .models.collection import Collection
    from .models.card import Card
    
    # Verify collection ownership
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get all cards in the collection
    cards = db.query(Card).filter(Card.collection_id == collection_id).all()
    
    if not cards:
        raise HTTPException(status_code=400, detail="No cards found in collection")
    
    # Convert to eBay-compliant CSV format using the existing function from main.py
    csv_data = []
    for i, card in enumerate(cards):
        # Build eBay-compliant title (80 char max)
        title_parts = []
        if card.year:
            title_parts.append(str(card.year))
        if card.set_name:
            title_parts.append(card.set_name)
        if card.player_name:
            title_parts.append(card.player_name)
        if card.card_number:
            title_parts.append(f"#{card.card_number}")
        if card.parallel:
            title_parts.append(card.parallel)
        
        title = " ".join(title_parts)[:80] if title_parts else "Trading Card"
        
        # Build description
        description_parts = []
        if card.player_name:
            description_parts.append(f"Player: {card.player_name}")
        if card.set_name:
            description_parts.append(f"Set: {card.set_name}")
        if card.year:
            description_parts.append(f"Year: {card.year}")
        if card.card_number:
            description_parts.append(f"Card Number: {card.card_number}")
        if card.parallel:
            description_parts.append(f"Parallel: {card.parallel}")
        if card.manufacturer:
            description_parts.append(f"Manufacturer: {card.manufacturer}")
        
        description = "<br>".join(description_parts) if description_parts else "Trading Card"
        
        # Determine price
        start_price = "9.99"
        if card.price_data and isinstance(card.price_data, dict):
            estimated_value = card.price_data.get('estimated_value')
            if estimated_value:
                try:
                    price = float(estimated_value)
                    start_price = f"{price:.2f}"
                except (ValueError, TypeError):
                    start_price = "9.99"
        
        # Determine brand
        brand = "Unbranded"
        if card.set_name:
            set_name = card.set_name.upper()
            if 'TOPPS' in set_name:
                brand = "Topps"
            elif 'PANINI' in set_name:
                brand = "Panini"
            elif 'DONRUSS' in set_name:
                brand = "Donruss"
            elif 'BOWMAN' in set_name:
                brand = "Bowman"
            elif 'UPPER DECK' in set_name:
                brand = "Upper Deck"
        
        csv_row = {
            # REQUIRED eBay fields
            "Action": "Add",
            "Custom label (SKU)": f"CARD-{i+1:03d}",
            "Category ID": "213",  # Sports Trading Cards category
            "Title": title,
            "Condition ID": "1000",  # New condition
            "P:UPC": "Does not apply",
            "Item photo URL": "",  # Will be populated with actual image URLs
            "Format": "FixedPrice",
            "Description": description,
            "Duration": "GTC",  # Good Till Cancelled
            "Start price": start_price,
            "Quantity": "1",
            "Location": "United States",
            "Shipping profile name": "Free Domestic Shipping",
            "Return profile name": "30 Day Returns",
            "Payment profile name": "Standard Payment",
            
            # Item specifics for trading cards
            "C:Brand": brand,
            "C:Player": card.player_name or '',
            "C:Set": card.set_name or '',
            "C:Year": card.year or '',
            "C:Card Number": card.card_number or '',
            "C:Parallel/Variety": card.parallel or '',
            "C:Features": card.features or ''
        }
        csv_data.append(csv_row)
    
    # Create DataFrame and generate CSV
    df = pd.DataFrame(csv_data)
    
    # Create in-memory CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Create response
    response = StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type='text/csv',
        headers={"Content-Disposition": f"attachment; filename={collection.name}_ebay_export.csv"}
    )
    
    return response

# Analytics routes
@app.get("/api/v1/analytics")
async def get_analytics(
    current_user: User = Depends(get_auth_service().get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get comprehensive analytics for the current user's collection"""
    analytics = analytics_service.get_user_analytics(current_user.id)
    return analytics

@app.get("/api/v1/analytics/collection/{collection_id}")
async def get_collection_analytics(
    collection_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get detailed analytics for a specific collection"""
    analytics = analytics_service.get_collection_analytics(collection_id, current_user.id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Collection not found")
    return analytics

@app.get("/api/v1/analytics/market")
async def get_market_insights(
    current_user: User = Depends(get_auth_service().get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get market insights and trends"""
    insights = analytics_service.get_market_insights(current_user.id)
    return insights

# Price routes
@app.get("/api/v1/cards/{card_id}/price")
async def get_card_price(
    card_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service),
    price_service: PriceService = Depends(get_price_service)
):
    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    price_data = await price_service.research_price(card.__dict__)
    if not price_data:
        raise HTTPException(status_code=404, detail="Price data not found")
    
    return {
        "estimated_value": price_data['estimated_value'],
        "listing_price": price_data['listing_price'],
        "confidence": price_data['confidence'],
        "source": price_data['source']
    }

# -----------------------------------------------------------------------------
# Price history route
# -----------------------------------------------------------------------------

@app.get("/api/v1/cards/{card_id}/history")
async def get_card_price_history(
    card_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service),
    price_service: PriceService = Depends(get_price_service),
):
    """Return chronological price history for a card owned by the current user."""
    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Authorization: make sure card belongs to current user via collection relationship
    if not card.collection or card.collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this card")

    history_points = price_service.get_price_history(card_id)
    return history_points

# 🚀 NEW: Hybrid Pricing Routes
@app.post("/api/v1/pricing/hybrid")
async def get_hybrid_price(
    card_data: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    hybrid_service: HybridPricingService = Depends(get_hybrid_pricing_service)
):
    """Get price using hybrid approach (local DB + eBay fallback)"""
    try:
        result = await hybrid_service.get_card_price(card_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/pricing/database/search")
async def search_card_database(
    query: str,
    sport: str = None,
    year: int = None,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_db_service: CardDatabaseService = Depends(get_card_database_service)
):
    """Search the local card database"""
    results = card_db_service.search_cards(query, sport, year)
    return [
        {
            "id": card.id,
            "player": card.player_name,
            "set": card.set_name,
            "year": card.year,
            "manufacturer": card.manufacturer,
            "card_number": card.card_number,
            "parallel": card.parallel,
            "raw_price": card.avg_raw_price,
            "psa9_price": card.avg_psa9_price,
            "psa10_price": card.avg_psa10_price,
            "last_updated": card.last_updated,
            "sport": card.sport
        }
        for card in results
    ]

@app.get("/api/v1/pricing/database/popular/{sport}")
async def get_popular_cards(
    sport: str,
    year: int,
    limit: int = 20,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_db_service: CardDatabaseService = Depends(get_card_database_service)
):
    """Get popular cards for a sport and year"""
    results = card_db_service.get_popular_cards(sport.upper(), year, limit)
    return [
        {
            "player": card.player_name,
            "set": card.set_name,
            "card_number": card.card_number,
            "parallel": card.parallel,
            "psa10_price": card.avg_psa10_price,
            "rookie": card.rookie
        }
        for card in results
    ]

# -----------------------------------------------------------------------------
# eBay integration
# -----------------------------------------------------------------------------

@app.get("/api/v1/ebay/auth-url")
async def get_ebay_authorization_url(
    current_user: User = Depends(get_auth_service().get_current_user),
    ebay_service: EbayService = Depends(get_ebay_service),
):
    """Generate an eBay OAuth2 authorization URL for the user to grant access."""
    state = current_user.id  # Simple CSRF mitigation
    url = ebay_service.get_authorization_url(state)
    return {"authorization_url": url}


@app.post("/api/v1/ebay/list")
async def create_ebay_listing(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service),
    price_service: PriceService = Depends(get_price_service),
    ebay_service: EbayService = Depends(get_ebay_service),
):
    """Create eBay listing for a specific card.
    Expects payload {card_id: str, access_token: str, price_markup?: float}
    """
    card_id = payload.get("card_id")
    access_token = payload.get("access_token")
    price_markup = float(payload.get("price_markup", 0.15))

    if not card_id or not access_token:
        raise HTTPException(status_code=400, detail="card_id and access_token required")

    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if not card.collection or card.collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to list this card")

    # Determine listing price
    estimated_value = card.price_data.get("estimated_value") if card.price_data else None
    if not estimated_value:
        pricing = await price_service.research_price(card.__dict__)
        estimated_value = pricing["estimated_value"] if pricing else 1.0

    listing_price = round(estimated_value * (1 + price_markup), 2)

    title_parts = [str(card.year or ""), card.manufacturer or "", card.set_name or "", card.player_name or "", f"#{card.card_number}" if card.card_number else ""]
    title = " ".join([part for part in title_parts if part]).strip()
    description = f"{title} - Automated listing via FlipHero"

    try:
        result = ebay_service.create_listing(access_token, title=title, description=description, price=listing_price)
        return {"status": "success", "ebay_offer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/collections/{collection_id}/create-listings")
async def create_collection_listings(
    collection_id: str,
    current_user: User = Depends(get_auth_service().get_current_user),
    db: Session = Depends(get_db)
):
    """Create eBay listings for all cards in a collection (demo endpoint)"""
    from .models.collection import Collection
    from .models.card import Card
    
    # Verify collection ownership
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get all cards in the collection
    cards = db.query(Card).filter(Card.collection_id == collection_id).all()
    
    if not cards:
        raise HTTPException(status_code=400, detail="No cards found in collection")
    
    # For now, return a demo response showing what would be listed
    # In production, this would connect to eBay API
    
    listings = []
    for card in cards:
        estimated_value = 1.0
        if card.price_data and isinstance(card.price_data, dict):
            estimated_value = card.price_data.get('estimated_value', 1.0)
        
        listing_price = round(estimated_value * 1.15, 2)  # 15% markup
        
        title_parts = []
        if card.year:
            title_parts.append(str(card.year))
        if card.set_name:
            title_parts.append(card.set_name)
        if card.player_name:
            title_parts.append(card.player_name)
        if card.card_number:
            title_parts.append(f"#{card.card_number}")
        
        title = " ".join(title_parts)[:80] if title_parts else "Trading Card"
        
        listings.append({
            "card_id": card.id,
            "title": title,
            "estimated_value": estimated_value,
            "listing_price": listing_price,
            "status": "ready"  # In production: "created", "pending", "error"
        })
    
    return {
        "status": "success",
        "collection_name": collection.name,
        "total_cards": len(cards),
        "total_value": sum(l["estimated_value"] for l in listings),
        "total_listing_value": sum(l["listing_price"] for l in listings),
        "listings": listings
    }

# -----------------------------------------------------------------------------
# Billing & Subscription endpoints
# -----------------------------------------------------------------------------

@app.post("/api/v1/billing/checkout")
async def create_checkout_session(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Create Stripe checkout session for Pro subscription"""
    plan = payload.get("plan", "pro_monthly")
    discount_code = payload.get("discount_code")
    
    if plan not in STRIPE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    price_id = STRIPE_PRICES[plan]
    success_url = payload.get("success_url", "http://localhost:3000/dashboard/billing?success=true")
    cancel_url = payload.get("cancel_url", "http://localhost:3000/dashboard/billing?cancelled=true")
    
    return billing_service.create_checkout_session(
        user=current_user,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        discount_code=discount_code
    )

@app.post("/api/v1/billing/webhook")
async def stripe_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
):
    """Handle Stripe webhook events (no authentication required)"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    return billing_service.handle_webhook(payload, sig_header)

@app.get("/api/v1/billing/subscription")
async def get_subscription(
    current_user: User = Depends(get_auth_service().get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Get current user's subscription details"""
    subscription = billing_service.get_user_subscription(current_user.id)
    if not subscription:
        return {"plan_type": "free", "status": "active"}
    
    return {
        "plan_type": subscription.plan_type,
        "status": subscription.status,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "stripe_subscription_id": subscription.stripe_subscription_id
    }

@app.post("/api/v1/billing/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_auth_service().get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Cancel user's subscription"""
    return billing_service.cancel_subscription(current_user)

@app.post("/api/v1/billing/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_auth_service().get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Reactivate user's subscription"""
    return billing_service.reactivate_subscription(current_user)

# -----------------------------------------------------------------------------
# Direct GCS upload helper (Option B)
# -----------------------------------------------------------------------------

@app.post("/api/v1/uploads/signed-url")
async def generate_signed_upload_url(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """Return a short-lived signed URL so the frontend can upload an image
    directly to Google Cloud Storage.

    Expected JSON payload:
      {
        "content_type": "image/jpeg",   # required
        "filename": "mycard.jpg"        # optional, for nicer extension
      }
    """
    content_type = payload.get("content_type")
    if not content_type:
        raise HTTPException(status_code=400, detail="content_type is required")

    filename = payload.get("filename")

    try:
        url_data = upload_service.generate_signed_put_url(content_type, filename)
        return url_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cards/process-url")
async def process_card_from_url(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    """Process a card from a GCS image URL (Option B completion).
    
    Expected JSON payload:
      {
        "image_url": "https://storage.googleapis.com/bucket/path/image.jpg",
        "collection_id": "uuid",
        "filename": "optional-original-name.jpg"  # for player name extraction
      }
    """
    image_url = payload.get("image_url")
    collection_id = payload.get("collection_id")
    filename = payload.get("filename", "unknown.jpg")
    
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    if not collection_id:
        raise HTTPException(status_code=400, detail="collection_id is required")
    
    try:
        # Download the image from GCS for OCR processing
        import requests
        import tempfile
        import os
        from ..utils.enhanced_card_processor import process_all_images_enhanced
        from ..utils.enhanced_card_processor import _extract_player_from_filename
        
        # Download image
        img_response = requests.get(image_url, timeout=10)
        if img_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Could not download image: {img_response.status_code}")
        
        # Save to temp file for OCR
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(img_response.content)
            temp_path = temp_file.name
        
        try:
            # Extract player name from filename
            player_name = _extract_player_from_filename(filename)
            
            # Process with OCR
            processed_cards = process_all_images_enhanced([temp_path])
            if processed_cards and len(processed_cards) > 0:
                card_data = processed_cards[0]
                # Override player name with filename if extracted
                if player_name:
                    card_data["player"] = player_name
            else:
                # Fallback if OCR fails
                card_data = {
                    "player": player_name or "Unknown Player",
                    "set": "Unknown Set",
                    "year": "Unknown",
                    "card_number": "",
                    "parallel": "",
                    "manufacturer": "Unknown",
                    "features": "",
                    "graded": False,
                    "grade": "",
                    "grading_company": "",
                    "cert_number": "",
                    "filename": filename
                }
            
            # Get hybrid pricing
            try:
                hybrid_service = card_service.hybrid_pricing_service
                hybrid_pricing_result = await hybrid_service.get_card_price(card_data)
                
                price_data = {
                    "estimated_value": hybrid_pricing_result.get('estimated_value', 0.0),
                    "listing_price": hybrid_pricing_result.get('estimated_value', 0.0) * 1.15,
                    "confidence": hybrid_pricing_result.get('confidence', 'unknown'),
                    "source": hybrid_pricing_result.get('source', 'unknown'),
                    "method": hybrid_pricing_result.get('method', 'unknown'),
                    "sample_size": hybrid_pricing_result.get('sample_size', 0),
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }
                
            except Exception as pricing_error:
                print(f"❌ Hybrid pricing failed: {pricing_error}")
                price_data = {
                    "estimated_value": 1.0,
                    "listing_price": 1.15,
                    "confidence": "low",
                    "source": "fallback",
                    "method": "default",
                    "sample_size": 0,
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }
            
            # Create card record with GCS image URL
            from ..models.card import Card, CardImage
            card = Card(
                collection_id=collection_id,
                player_name=card_data.get('player', ''),
                set_name=card_data.get('set', ''),
                year=card_data.get('year', ''),
                card_number=card_data.get('card_number', ''),
                parallel=card_data.get('parallel', ''),
                manufacturer=card_data.get('manufacturer', ''),
                features=card_data.get('features', ''),
                graded=card_data.get('graded', False),
                grade=card_data.get('grade', ''),
                grading_company=card_data.get('grading_company', ''),
                cert_number=card_data.get('cert_number', ''),
                price_data=price_data or {}
            )
            card_service.db.add(card)
            card_service.db.commit()
            card_service.db.refresh(card)
            
            # Create image record pointing to GCS URL
            card_image = CardImage(
                card_id=card.id,
                image_url=image_url,  # Store the GCS public URL
                image_type='front'
            )
            card_service.db.add(card_image)
            card_service.db.commit()
            
            # Add to price history
            if price_data and isinstance(price_data, dict):
                estimated_value = price_data.get("estimated_value")
                if isinstance(estimated_value, (int, float)):
                    try:
                        card_service.price_service.add_price_history(
                            card.id, 
                            float(estimated_value), 
                            price_source=price_data.get("source", "unknown")
                        )
                    except Exception as history_err:
                        print(f"⚠️  Failed to record price history: {history_err}")
            
            return {
                "card_id": card.id,
                "card_data": {
                    "player": card.player_name,
                    "set": card.set_name,
                    "year": card.year,
                    "card_number": card.card_number,
                    "parallel": card.parallel,
                    "manufacturer": card.manufacturer,
                    "features": card.features,
                    "graded": card.graded,
                    "grade": card.grade,
                    "grading_company": card.grading_company,
                    "cert_number": card.cert_number
                },
                "price_data": price_data,
                "image_url": image_url
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cards/process-dual-side")
async def process_dual_side_card_endpoint(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    """Process a card with both front and back images for enhanced OCR.
    
    Expected JSON payload:
      {
        "front_image_url": "https://storage.googleapis.com/bucket/path/front.jpg",
        "back_image_url": "https://storage.googleapis.com/bucket/path/back.jpg",  # optional
        "collection_id": "uuid",
        "filename": "optional-original-name.jpg"  # for player name extraction
      }
    """
    front_image_url = payload.get("front_image_url")
    back_image_url = payload.get("back_image_url")
    collection_id = payload.get("collection_id")
    filename = payload.get("filename", "unknown.jpg")
    
    if not front_image_url:
        raise HTTPException(status_code=400, detail="front_image_url is required")
    if not collection_id:
        raise HTTPException(status_code=400, detail="collection_id is required")
    
    try:
        import requests
        import tempfile
        import os
        from ..utils.enhanced_card_processor import process_dual_side_card
        from ..utils.enhanced_card_processor import _extract_player_from_filename
        
        # Download front image
        front_response = requests.get(front_image_url, timeout=10)
        if front_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Could not download front image: {front_response.status_code}")
        
        # Save front to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix="_front.jpg") as temp_file:
            temp_file.write(front_response.content)
            front_temp_path = temp_file.name
        
        back_temp_path = None
        
        # Download back image if provided
        if back_image_url:
            try:
                back_response = requests.get(back_image_url, timeout=10)
                if back_response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix="_back.jpg") as temp_file:
                        temp_file.write(back_response.content)
                        back_temp_path = temp_file.name
                else:
                    print(f"⚠️  Could not download back image: {back_response.status_code}")
            except Exception as e:
                print(f"⚠️  Back image download failed: {e}")
        
        try:
            # Extract player name from filename
            player_name = _extract_player_from_filename(filename)
            
            # Process with dual-side OCR
            card_data = process_dual_side_card(front_temp_path, back_temp_path, player_name)
            
            if not card_data:
                # Fallback if OCR fails
                card_data = {
                    "player": player_name or "Unknown Player",
                    "set": "Unknown Set",
                    "year": "Unknown",
                    "card_number": "",
                    "parallel": "",
                    "manufacturer": "Unknown",
                    "features": "",
                    "graded": False,
                    "grade": "",
                    "grading_company": "",
                    "cert_number": "",
                    "confidence_score": 0.2,
                    "dual_side": back_image_url is not None,
                    "filename": filename
                }
            
            # Get hybrid pricing
            try:
                hybrid_service = card_service.hybrid_pricing_service
                hybrid_pricing_result = await hybrid_service.get_card_price(card_data)
                
                price_data = {
                    "estimated_value": hybrid_pricing_result.get('estimated_value', 0.0),
                    "listing_price": hybrid_pricing_result.get('estimated_value', 0.0) * 1.15,
                    "confidence": hybrid_pricing_result.get('confidence', 'unknown'),
                    "source": hybrid_pricing_result.get('source', 'unknown'),
                    "method": hybrid_pricing_result.get('method', 'unknown'),
                    "sample_size": hybrid_pricing_result.get('sample_size', 0),
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }
                
            except Exception as pricing_error:
                print(f"❌ Hybrid pricing failed: {pricing_error}")
                price_data = {
                    "estimated_value": 1.0,
                    "listing_price": 1.15,
                    "confidence": "low",
                    "source": "fallback",
                    "method": "default",
                    "sample_size": 0,
                    "search_query": f"{card_data.get('player', 'Unknown')} {card_data.get('set', 'Unknown')}"
                }
            
            # Create card record
            from ..models.card import Card, CardImage
            card = Card(
                collection_id=collection_id,
                player_name=card_data.get('player', ''),
                set_name=card_data.get('set', ''),
                year=card_data.get('year', ''),
                card_number=card_data.get('card_number', ''),
                parallel=card_data.get('parallel', ''),
                manufacturer=card_data.get('manufacturer', ''),
                features=card_data.get('features', ''),
                graded=card_data.get('graded', False),
                grade=card_data.get('grade', ''),
                grading_company=card_data.get('grading_company', ''),
                cert_number=card_data.get('cert_number', ''),
                price_data=price_data or {}
            )
            card_service.db.add(card)
            card_service.db.commit()
            card_service.db.refresh(card)
            
            # Create image records for both sides
            front_image = CardImage(
                card_id=card.id,
                image_url=front_image_url,
                image_type='front'
            )
            card_service.db.add(front_image)
            
            if back_image_url:
                back_image = CardImage(
                    card_id=card.id,
                    image_url=back_image_url,
                    image_type='back'
                )
                card_service.db.add(back_image)
            
            card_service.db.commit()
            
            # Add to price history
            if price_data and isinstance(price_data, dict):
                estimated_value = price_data.get("estimated_value")
                if isinstance(estimated_value, (int, float)):
                    try:
                        card_service.price_service.add_price_history(
                            card.id, 
                            float(estimated_value), 
                            price_source=price_data.get("source", "unknown")
                        )
                    except Exception as history_err:
                        print(f"⚠️  Failed to record price history: {history_err}")
            
            return {
                "card_id": card.id,
                "card_data": {
                    "player": card.player_name,
                    "set": card.set_name,
                    "year": card.year,
                    "card_number": card.card_number,
                    "parallel": card.parallel,
                    "manufacturer": card.manufacturer,
                    "features": card.features,
                    "graded": card.graded,
                    "grade": card.grade,
                    "grading_company": card.grading_company,
                    "cert_number": card.cert_number,
                    "confidence_score": card_data.get('confidence_score', 0.0),
                    "dual_side": card_data.get('dual_side', False),
                    "ocr_sources": card_data.get('ocr_sources', 'front')
                },
                "price_data": price_data,
                "front_image_url": front_image_url,
                "back_image_url": back_image_url
            }
            
        finally:
            # Clean up temp files
            for temp_path in [front_temp_path, back_temp_path]:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/uploads/signed-urls-dual")
async def generate_dual_signed_urls(
    payload: dict,
    current_user: User = Depends(get_auth_service().get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """Generate signed URLs for both front and back images of a card.
    
    Expected JSON payload:
      {
        "content_type": "image/jpeg",
        "front_filename": "card-front.jpg",  # optional
        "back_filename": "card-back.jpg"     # optional
      }
    """
    content_type = payload.get("content_type")
    front_filename = payload.get("front_filename")
    back_filename = payload.get("back_filename")
    
    if not content_type:
        raise HTTPException(status_code=400, detail="content_type is required")
    
    try:
        # Generate signed URL for front
        front_data = upload_service.generate_signed_put_url(
            content_type=content_type,
            filename=front_filename
        )
        
        # Generate signed URL for back  
        back_data = upload_service.generate_signed_put_url(
            content_type=content_type,
            filename=back_filename
        )
        
        return {
            "front": {
                "upload_url": front_data["upload_url"],
                "public_url": front_data["public_url"],
                "blob_name": front_data["blob_name"],
                "expires_in": front_data["expires_in"]
            },
            "back": {
                "upload_url": back_data["upload_url"],
                "public_url": back_data["public_url"],
                "blob_name": back_data["blob_name"],
                "expires_in": back_data["expires_in"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 