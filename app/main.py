from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers import health, items, air_quality

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Boilerplate FastAPI + Supabase, listo para desplegar en Vercel.",
    version="0.1.0",
)

# CORS: necesario para que tu frontend (v0 / Vercel) pueda llamar a esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(items.router)
app.include_router(air_quality.router)


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} API funcionando 🚀"}
