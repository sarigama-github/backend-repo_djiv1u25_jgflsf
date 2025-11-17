import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

from database import db, create_document, get_documents

app = FastAPI(title="Luxe Parfumerie API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductIn(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    image: Optional[str] = Field(None, description="Image URL")
    in_stock: bool = Field(True, description="Whether product is in stock")


@app.get("/")
def read_root():
    return {"message": "Luxe Parfumerie Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', "✅ Connected")
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility: convert Mongo documents to JSON-safe dicts
from bson import ObjectId

def serialize_product(doc: dict) -> dict:
    if not doc:
        return {}
    result = {k: v for k, v in doc.items() if k != "_id"}
    if doc.get("_id"):
        result["id"] = str(doc["_id"])
    return result


@app.get("/api/products", response_model=List[dict])
def list_products(limit: int = 20):
    """List products. If the collection is empty, returns an empty list."""
    try:
        docs = get_documents("product", {}, limit)
        return [serialize_product(d) for d in docs]
    except Exception as e:
        # Database might not be configured; provide graceful empty response
        return []


@app.post("/api/products", status_code=201)
def create_product(product: ProductIn):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        new_id = create_document("product", product.model_dump())
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed", summary="Seed sample perfume & beauty products")
def seed_products():
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Only seed if collection is empty
    existing = db["product"].count_documents({})
    if existing > 0:
        return {"seeded": False, "message": "Products already exist"}

    samples: List[ProductIn] = [
        ProductIn(
            title="Noir Absolu Eau de Parfum",
            description="A sultry blend of black amber, cedarwood, and velvet musk.",
            price=189.00,
            category="Perfume",
            image="https://images.unsplash.com/photo-1585386959984-a41552231658?q=80&w=1200",
        ),
        ProductIn(
            title="Silk Veil Setting Powder",
            description="Ultra-fine translucent powder for a soft-focus matte finish.",
            price=48.00,
            category="Beauty",
            image="https://images.unsplash.com/photo-1596461404969-9ae70bba3a94?q=80&w=1200",
        ),
        ProductIn(
            title="Chrome Iris Eau de Toilette",
            description="Iridescent florals with a cool metallic accord and white musk.",
            price=129.00,
            category="Perfume",
            image="https://images.unsplash.com/photo-1605296867724-fa87a8ef53fd?q=80&w=1200",
        ),
        ProductIn(
            title="Velvet Matte Lip Color",
            description="Comfort-matte lipstick with saturated pigment and skincare oils.",
            price=32.00,
            category="Beauty",
            image="https://images.unsplash.com/photo-1589984662646-e7b2e4962f85?q=80&w=1200",
        ),
    ]

    for p in samples:
        create_document("product", p.model_dump())

    return {"seeded": True, "count": len(samples)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
