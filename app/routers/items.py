"""
Router de ejemplo con CRUD completo. Este es el patrón que copiarás
y adaptarás para cada demo/proyecto nuevo.

Asume una tabla `items` en Supabase con columnas:
    id (uuid, pk, default gen_random_uuid())
    user_id (uuid, fk -> auth.users.id)
    title (text)
    description (text, nullable)
    created_at (timestamptz, default now())

Y una política RLS típica:
    create policy "Users can CRUD their own items"
    on items for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
"""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user, CurrentUser
from app.core.database import get_supabase_client
from app.models.item import ItemCreate, ItemUpdate, ItemResponse

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[ItemResponse])
def list_items(user: CurrentUser = Depends(get_current_user)):
    db = get_supabase_client(user.access_token)
    result = db.table("items").select("*").order("created_at", desc=True).execute()
    return result.data


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, user: CurrentUser = Depends(get_current_user)):
    db = get_supabase_client(user.access_token)
    payload = item.model_dump()
    payload["user_id"] = user.id
    result = db.table("items").insert(payload).execute()
    return result.data[0]


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_supabase_client(user.access_token)
    result = db.table("items").select("*").eq("id", item_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return result.data[0]


@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(item_id: str, item: ItemUpdate, user: CurrentUser = Depends(get_current_user)):
    db = get_supabase_client(user.access_token)
    payload = {k: v for k, v in item.model_dump().items() if v is not None}
    result = db.table("items").update(payload).eq("id", item_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return result.data[0]


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_supabase_client(user.access_token)
    db.table("items").delete().eq("id", item_id).execute()
    return None
