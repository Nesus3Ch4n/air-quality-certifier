from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Endpoint simple para verificar que la API y el deploy están vivos."""
    return {"status": "ok"}
