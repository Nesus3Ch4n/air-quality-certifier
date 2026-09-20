"""
Modelos para el módulo de calidad del aire.

`AirQualityReading` es la lectura ya normalizada desde la fuente (CKAN,
estación La Flora - Cali). `AirQualityRecord` es lo que se guarda/devuelve,
incluyendo el hash de integridad, la clasificación IQCA oficial y el anclaje
on-chain en Ethereum.

Clasificación: Índice de Calidad del Aire (IQCA) colombiano según la
Resolución 2254 de 2017 del Ministerio de Ambiente y Desarrollo Sostenible.
"""
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class AirQualityReading(BaseModel):
    station: str
    recorded_at: datetime | None = None
    pm10: float | None = None
    so2: float | None = None
    no2: float | None = None
    co: float | None = None
    o3: float | None = None
    h2s: float | None = None
    wind_speed: float | None = None
    wind_dir: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    radiation: float | None = None
    rain: float | None = None


class IQCAClassification(BaseModel):
    """
    Clasificación oficial IQCA según Resolución 2254 de 2017 (MADS Colombia).
    Basada en promedio móvil de 24h de PM10.
    """
    category: str    # "Buena" | "Aceptable" | "Dañina a grupos sensibles" | "Dañina" | "Muy dañina" | "Peligrosa"
    color: str       # "Verde" | "Amarillo" | "Naranja" | "Rojo" | "Morado" | "Marrón"
    color_hex: str   # código hex para frontend
    index_min: int   # rango inferior del índice IQCA
    index_max: int   # rango superior del índice IQCA (999 = sin límite superior)
    health_message: str  # mensaje de salud pública oficial


class AirQualityRecord(AirQualityReading):
    id: UUID | None = None

    # Clasificación IQCA oficial (Resolución 2254 de 2017)
    iqca_category: str           # categoría oficial: "Buena", "Aceptable", etc.
    iqca_color: str              # color oficial: "Verde", "Amarillo", etc.
    iqca_color_hex: str          # hex para el frontend
    iqca_index: int | None = None  # valor numérico del índice (0-500+)
    iqca_health_message: str     # mensaje oficial de salud pública

    sha256_hash: str             # huella SHA-256 de integridad del registro

    # Anclaje on-chain en Ethereum
    tx_hash: str | None = None          # hash de la transacción en Ethereum
    block_number: int | None = None     # bloque donde quedó confirmado
    chain_id: int | None = None         # ID de la red (p.ej. 177 = HashKey Chain)

    created_at: datetime | None = None
