"""
Modelo de ejemplo. Reemplázalo por las entidades reales de cada demo
(ej. Producto, Pedido, Cliente, Tarea, etc.)
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ItemResponse(ItemBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
