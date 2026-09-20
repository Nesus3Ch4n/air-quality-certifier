"""
Configuración central del proyecto.
Lee variables de entorno usando pydantic-settings para validación automática.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str  # Solo se usa en el backend, NUNCA la expongas al frontend
    SUPABASE_JWT_SECRET: str        # Para verificar tokens de usuarios autenticados

    # --- App ---
    APP_NAME: str = "Certificador de Calidad del Aire Cali"
    ENVIRONMENT: str = "development"  # development | production
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # separa múltiples con coma

    # --- Blockchain (Ethereum / HashKey Chain) ---
    # Pon BLOCKCHAIN_ENABLED=false para correr sin wallet (modo DRY_RUN)
    BLOCKCHAIN_ENABLED: bool = False

    # URL RPC del nodo. Por defecto HashKey Chain testnet.
    # Mainnet:  https://mainnet.hsk.xyz
    # Testnet:  https://hashkeychain-testnet.alt.technology
    BLOCKCHAIN_RPC_URL: str = "https://hashkeychain-testnet.alt.technology"

    # Dirección del contrato AirQualityCertifier ya desplegado
    BLOCKCHAIN_CONTRACT_ADDRESS: str = ""

    # Clave privada de la wallet certificadora (NUNCA la subas a git)
    BLOCKCHAIN_PRIVATE_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cachea la instancia de Settings para no releer el .env en cada request."""
    return Settings()
