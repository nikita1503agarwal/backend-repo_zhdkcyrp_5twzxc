import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Slot, Order, OrderItem

app = FastAPI(title="Grocery Shop API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# Seed initial data endpoint (idempotent)
@app.post("/seed")
def seed():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    # Seed products if empty
    if db["product"].count_documents({}) == 0:
        products = [
            {"name": "Bananas", "price": 0.79, "unit": "each", "stock": 200, "category": "Produce", "in_stock": True,
             "image": "https://images.unsplash.com/photo-1571772996211-2f02c9727629?w=400&q=80"},
            {"name": "Milk", "price": 2.49, "unit": "1L", "stock": 120, "category": "Dairy", "in_stock": True,
             "image": "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=400&q=80"},
            {"name": "Bread", "price": 1.99, "unit": "loaf", "stock": 80, "category": "Bakery", "in_stock": True,
             "image": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80"},
            {"name": "Eggs", "price": 3.49, "unit": "12", "stock": 90, "category": "Dairy", "in_stock": True,
             "image": "https://images.unsplash.com/photo-1517959105821-eaf2591984dd?w=400&q=80"},
        ]
        for p in products:
            create_document("product", p)

    # Seed pickup slots for today and tomorrow if empty
    if db["slot"].count_documents({}) == 0:
        slots = [
            {"label": "Today 10:00–10:30", "capacity": 10, "booked": 0},
            {"label": "Today 10:30–11:00", "capacity": 10, "booked": 0},
            {"label": "Today 5:00–5:30", "capacity": 12, "booked": 0},
            {"label": "Tomorrow 10:00–10:30", "capacity": 10, "booked": 0},
            {"label": "Tomorrow 5:00–5:30", "capacity": 12, "booked": 0},
        ]
        for s in slots:
            create_document("slot", s)

    return {"message": "Seed complete"}

# Public endpoints

@app.get("/products")
def list_products():
    docs = get_documents("product", {"in_stock": True})
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.get("/slots")
def list_slots():
    slots = get_documents("slot", {})
    for s in slots:
        s["id"] = str(s.pop("_id"))
        s["available"] = max(s.get("capacity", 0) - s.get("booked", 0), 0)
    return slots

class CreateOrderRequest(BaseModel):
    customer_name: str
    phone: str
    slot_id: str
    items: List[OrderItem]
    note: Optional[str] = None

@app.post("/orders")
def create_order(payload: CreateOrderRequest):
    # Validate slot availability
    slot = db["slot"].find_one({"_id": oid(payload.slot_id)})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    available = max(slot.get("capacity", 0) - slot.get("booked", 0), 0)
    if available <= 0:
        raise HTTPException(status_code=400, detail="Selected slot is full")

    # Compute total and verify products
    total = 0.0
    items_doc = []
    for item in payload.items:
        prod = db["product"].find_one({"_id": oid(item.product_id), "in_stock": True})
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        line_total = float(prod.get("price", 0)) * item.qty
        total += line_total
        items_doc.append({
            "product_id": item.product_id,
            "name": prod.get("name"),
            "unit": prod.get("unit"),
            "price": float(prod.get("price")),
            "qty": item.qty,
            "line_total": line_total,
        })

    order_doc = {
        "customer_name": payload.customer_name,
        "phone": payload.phone,
        "slot_id": payload.slot_id,
        "items": items_doc,
        "note": payload.note,
        "total": round(total, 2),
        "status": "confirmed",
    }
    order_id = create_document("order", order_doc)

    # Increment slot booked count
    db["slot"].update_one({"_id": slot["_id"]}, {"$inc": {"booked": 1}})

    return {"order_id": order_id, "total": order_doc["total"], "status": "confirmed"}

@app.get("/test")
def test_database():
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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
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
    return response

@app.get("/")
def root():
    return {"message": "Grocery Shop API running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
