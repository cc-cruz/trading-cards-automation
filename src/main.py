from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import get_db, engine, Base
from .services.auth_service import AuthService, get_auth_service, oauth2_scheme
from .services.card_service import CardService, get_card_service
from .services.price_service import PriceService, get_price_service
from .schemas.auth import Token, UserCreate, User
from .schemas.card import CardCreate, CardUpdate, Card as CardSchema

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
async def login(
    login_data: dict,
    db: Session = Depends(get_db)
):
    email = login_data.get("email")
    password = login_data.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    auth_service = get_auth_service(db)
    user = auth_service.authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/register", response_model=User)
async def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    auth_service = get_auth_service(db)
    return auth_service.create_user(user)

# Auth dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user"""
    auth_service = get_auth_service(db)
    return await auth_service.get_current_user(token)

@app.get("/api/v1/auth/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

# Card routes

@app.get("/api/v1/cards/recent")
async def get_recent_cards(
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    return await card_service.process_card_image(card.image, card.collection_id)

@app.get("/api/v1/cards/{card_id}", response_model=CardSchema)
async def get_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@app.get("/api/v1/collections/{collection_id}/cards", response_model=list[CardSchema])
async def get_collection_cards(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    return card_service.get_collection_cards(collection_id)

@app.put("/api/v1/cards/{card_id}", response_model=CardSchema)
async def update_card(
    card_id: str,
    card_update: CardUpdate,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    card = card_service.update_card(card_id, card_update)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@app.delete("/api/v1/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    success = card_service.delete_card(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"status": "success"}

# Collection routes
@app.get("/api/v1/collections")
async def get_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all collections for the current user"""
    from .models.collection import Collection
    collections = db.query(Collection).filter(Collection.user_id == current_user.id).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in collections]

@app.post("/api/v1/collections")
async def create_collection(
    collection_data: dict,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service)
):
    """Get collection statistics for the current user"""
    stats = card_service.get_user_collection_stats(current_user.id)
    return stats

# Price routes
@app.get("/api/v1/cards/{card_id}/price")
async def get_card_price(
    card_id: str,
    current_user: User = Depends(get_current_user),
    card_service: CardService = Depends(get_card_service),
    price_service: PriceService = Depends(get_price_service)
):
    card = card_service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    price_data = await price_service.research_price(card.__dict__)
    if not price_data:
        raise HTTPException(status_code=404, detail="Price data not found")
    
    return price_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 