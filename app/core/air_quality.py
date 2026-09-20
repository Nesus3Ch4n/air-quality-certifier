"""
Núcleo del "Certificador de Calidad del Aire".

Responsabilidades:
1. Traer lecturas crudas de las estaciones del DAGMA (Cali) vía la API
   pública de CKAN (datos.cali.gov.co).
2. Normalizarlas a nuestro esquema (AirQualityReading).
3. Calcular un hash SHA-256 por lectura → prueba de integridad: cualquier
   alteración posterior del dato cambia el hash.
4. Clasificar cada lectura con el IQCA oficial colombiano (Resolución 2254
   de 2017, Ministerio de Ambiente y Desarrollo Sostenible).
5. Retornar los AirQualityRecord listos para persistir y anclar on-chain.

─── Clasificación IQCA (Resolución 2254 / 2017 – MADS Colombia) ───────────
El Índice de Calidad del Aire (IQCA) colombiano se calcula sobre promedios
móviles de 24h para cada contaminante (PM10, PM2.5, O3, NO2, SO2, CO) y se
toma el peor. Para el MVP usamos PM10, el único parámetro disponible en la
fuente CKAN del DAGMA Cali.

Contaminante de referencia: PM10 (µg/m³), promedio 24h
│ IQCA   │ Categoría                      │ Color   │ PM10 (µg/m³) │
│  0–50  │ Buena                          │ Verde   │    0 – 54    │
│ 51–100 │ Aceptable                      │ Amarillo│   55 – 154   │
│101–150 │ Dañina a grupos sensibles      │ Naranja │  155 – 254   │
│151–200 │ Dañina                         │ Rojo    │  255 – 354   │
│201–300 │ Muy dañina                     │ Morado  │  355 – 424   │
│301–500 │ Peligrosa                      │ Marrón  │   ≥ 425      │

Nota: los datos horarios de CKAN no son promedios de 24h. Esta clasificación
se aplica sobre la lectura puntual como referencia rápida y es válida para
el MVP, pero debe comunicarse que el dictamen oficial requiere el promedio
móvil de 24h según el Artículo 9 de la Resolución 2254/2017.
"""
import hashlib
import json
import requests
from datetime import datetime, timezone
from dataclasses import dataclass
from app.models.air_quality import AirQualityReading, AirQualityRecord

CKAN_BASE_URL = "https://datos.cali.gov.co/api/3/action/datastore_search"

ESTACIONES = {
    "la_flora": "a83fcd9d-fd8e-44b1-96b4-102ed9c7326b",
    "canaveralejo": "b96b2baa-1f03-4f6a-ad7a-6b76ffb1e400",
}


# ─── Tabla IQCA oficial (Resolución 2254 / 2017 – MADS Colombia) ────────────
# Cada fila: (iqca_min, iqca_max, pm10_min, pm10_max, categoria, color, hex, mensaje)
@dataclass(frozen=True)
class _IQCABand:
    iqca_min: int
    iqca_max: int
    pm10_min: float
    pm10_max: float          # float('inf') para el último rango
    category: str
    color: str
    color_hex: str
    health_message: str


IQCA_BANDS: list[_IQCABand] = [
    _IQCABand(
        iqca_min=0, iqca_max=50,
        pm10_min=0, pm10_max=54,
        category="Buena",
        color="Verde",
        color_hex="#00E400",
        health_message=(
            "La calidad del aire es satisfactoria y la contaminación del aire "
            "representa poco o ningún riesgo."
        ),
    ),
    _IQCABand(
        iqca_min=51, iqca_max=100,
        pm10_min=55, pm10_max=154,
        category="Aceptable",
        color="Amarillo",
        color_hex="#FFFF00",
        health_message=(
            "La calidad del aire es aceptable. Sin embargo, puede haber riesgo "
            "para un pequeño número de personas inusualmente sensibles a la "
            "contaminación del aire."
        ),
    ),
    _IQCABand(
        iqca_min=101, iqca_max=150,
        pm10_min=155, pm10_max=254,
        category="Dañina a grupos sensibles",
        color="Naranja",
        color_hex="#FF7E00",
        health_message=(
            "Grupos sensibles (personas con enfermedades cardiacas o pulmonares, "
            "adultos mayores y niños) pueden experimentar efectos en su salud. "
            "El público en general tiene menos probabilidad de verse afectado."
        ),
    ),
    _IQCABand(
        iqca_min=151, iqca_max=200,
        pm10_min=255, pm10_max=354,
        category="Dañina",
        color="Rojo",
        color_hex="#FF0000",
        health_message=(
            "Toda la población puede comenzar a experimentar efectos en su salud. "
            "Los miembros de los grupos sensibles pueden experimentar efectos más "
            "graves. Se recomienda reducir la actividad física al aire libre."
        ),
    ),
    _IQCABand(
        iqca_min=201, iqca_max=300,
        pm10_min=355, pm10_max=424,
        category="Muy dañina",
        color="Morado",
        color_hex="#8F3F97",
        health_message=(
            "Advertencias de salud para condiciones de emergencia. "
            "Toda la población tiene más probabilidades de verse afectada. "
            "Evite actividades físicas al aire libre."
        ),
    ),
    _IQCABand(
        iqca_min=301, iqca_max=500,
        pm10_min=425, pm10_max=float("inf"),
        category="Peligrosa",
        color="Marrón",
        color_hex="#7E0023",
        health_message=(
            "Alerta máxima de salud: toda la población puede sufrir efectos "
            "graves. Permanezca en interiores y reduzca al mínimo la actividad "
            "física. Siga las instrucciones de las autoridades sanitarias."
        ),
    ),
]


def _to_float(value) -> float | None:
    """Los datos de CKAN vienen como texto; convierte de forma segura."""
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def fetch_raw_readings(estacion: str = "la_flora", limite: int = 20) -> list[dict]:
    """Trae las lecturas más recientes crudas desde CKAN."""
    resource_id = ESTACIONES[estacion]
    params = {
        "resource_id": resource_id,
        "limit": limite,
        "sort": '"Fecha & Hora" desc',
    }
    resp = requests.get(CKAN_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"CKAN respondió con error: {payload}")
    return payload["result"]["records"]


def normalize_reading(raw: dict, station: str) -> AirQualityReading:
    """Convierte una fila cruda de CKAN a nuestro esquema normalizado."""
    fecha_raw = raw.get("Fecha & Hora")
    recorded_at = None
    if fecha_raw:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                recorded_at = datetime.strptime(str(fecha_raw), fmt)
                break
            except ValueError:
                continue

    return AirQualityReading(
        station=station,
        recorded_at=recorded_at,
        pm10=_to_float(raw.get("PM10 (ug/m3)")),
        so2=_to_float(raw.get("SO2 (ug/m3)")),
        no2=_to_float(raw.get("NO2 (ug/m3)")),
        co=_to_float(raw.get("CO (ug/m3)")),
        o3=_to_float(raw.get("O3 (ug/m3)")),
        h2s=_to_float(raw.get("H2S (ug/m3)")),
        wind_speed=_to_float(raw.get("Vel Viento (m/s)")),
        wind_dir=_to_float(raw.get("Dir Viento (Grados)")),
        temperature=_to_float(raw.get("Temperatura (C°)")),
        humidity=_to_float(raw.get("Humedad (%)")),
        radiation=_to_float(raw.get("Radiacion Solar (Watt/M2)")),
        rain=_to_float(raw.get("Lluvia (mm)")),
    )


def classify_iqca(reading: AirQualityReading) -> _IQCABand | None:
    """
    Clasifica la lectura según el IQCA colombiano (Resolución 2254 / 2017).
    Contaminante de referencia: PM10.
    Retorna None si no hay dato de PM10.
    """
    if reading.pm10 is None:
        return None
    for band in IQCA_BANDS:
        if reading.pm10 <= band.pm10_max:
            return band
    # Por si acaso (no debería pasar con el último rango en inf)
    return IQCA_BANDS[-1]


def _interpolate_iqca_index(pm10: float) -> int:
    """
    Calcula el valor numérico del índice IQCA mediante interpolación lineal
    dentro del rango correspondiente, siguiendo la fórmula de la Res. 2254.
    """
    for band in IQCA_BANDS:
        if pm10 <= band.pm10_max:
            # Interpolación lineal: IQCA = ((IQCA_max - IQCA_min) / (C_max - C_min)) * (C - C_min) + IQCA_min
            c_range = band.pm10_max - band.pm10_min
            if c_range == 0 or band.pm10_max == float("inf"):
                return band.iqca_min
            ratio = (pm10 - band.pm10_min) / c_range
            return round(band.iqca_min + ratio * (band.iqca_max - band.iqca_min))
    return 500  # peligroso fuera de escala


def hash_reading(reading: AirQualityReading) -> str:
    """
    Calcula un SHA-256 determinístico de la lectura.
    JSON con claves ordenadas para que el mismo dato siempre
    produzca el mismo hash, sin importar el orden de los campos.
    """
    payload = reading.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_NO_DATA_BAND = _IQCABand(
    iqca_min=0, iqca_max=0,
    pm10_min=0, pm10_max=0,
    category="Sin dato",
    color="Gris",
    color_hex="#AAAAAA",
    health_message="No hay datos disponibles de PM10 para esta lectura.",
)


def get_certified_readings(estacion: str = "la_flora", limite: int = 20) -> list[AirQualityRecord]:
    """
    Flujo completo: trae, normaliza, clasifica con IQCA oficial y calcula el
    hash de integridad de las lecturas más recientes de una estación.
    Los registros quedan listos para persistir y anclar on-chain.
    """
    raw_readings = fetch_raw_readings(estacion, limite)
    records = []

    for raw in raw_readings:
        reading = normalize_reading(raw, station=estacion)
        band = classify_iqca(reading) or _NO_DATA_BAND
        iqca_index = _interpolate_iqca_index(reading.pm10) if reading.pm10 is not None else None

        record = AirQualityRecord(
            **reading.model_dump(),
            # Clasificación IQCA oficial
            iqca_category=band.category,
            iqca_color=band.color,
            iqca_color_hex=band.color_hex,
            iqca_index=iqca_index,
            iqca_health_message=band.health_message,
            # Integridad
            sha256_hash=hash_reading(reading),
            created_at=datetime.now(timezone.utc),
        )
        records.append(record)

    return records
