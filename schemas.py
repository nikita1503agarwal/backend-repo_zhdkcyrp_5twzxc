"""
Database Schemas for Grocery Shop App

Each Pydantic model maps to a MongoDB collection (lowercase of class name).
Use these for validation and consistent data handling.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class Product(BaseModel):
    """Grocery products available to order"""
    name: str = Field(..., description="Product name")
    price: float = Field(..., ge=0, description="Unit price")
    unit: str = Field(..., description="Unit label e.g. 'kg', 'each'")
    stock: int = Field(100, ge=0, description="Available stock units")
    image: Optional[str] = Field(None, description="Image URL")
    category: Optional[str] = Field(None, description="Category e.g. Produce, Dairy")
    in_stock: bool = Field(True, description="Whether product is available for ordering")

class Slot(BaseModel):
    """Pickup time slot with limited capacity to reduce in-store crowding"""
    label: str = Field(..., description="Human readable label e.g. 'Today 4:00–4:30 PM'")
    capacity: int = Field(..., ge=1, description="Max number of orders allowed in this slot")
    booked: int = Field(0, ge=0, description="Number of orders already booked")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Product ObjectId as string")
    qty: int = Field(..., ge=1, description="Quantity of the product")

class Order(BaseModel):
    """Customer order associated with a pickup slot"""
    customer_name: str = Field(...)
    phone: str = Field(...)
    slot_id: str = Field(..., description="Slot ObjectId as string")
    items: List[OrderItem] = Field(..., min_items=1)
    note: Optional[str] = Field(None)
    total: Optional[float] = Field(None, ge=0, description="Server-computed total")
