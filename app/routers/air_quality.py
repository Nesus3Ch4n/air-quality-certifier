"""
Endpoints del Certificador de Calidad del Aire — DAGMA Cali.

GET /air-quality/ingest
    Trae lecturas frescas del CKAN público, las clasifica con el IQCA oficial
    (Resolución 2254/2017), calcula el hash SHA-256 de integridad, las ancla
    on-chain en Ethereum/HashKey Chain y las persiste en Supabase.

GET /air-quality/
    Lista las lecturas ya certificadas guardadas en Supabase.

GET /air-quality/verify/{sha256_hash}
    Verifica on-chain si un hash concreto está certificado en el contrato.

GET /air-quality/stats
    Estadísticas globales: total de lecturas on-chain, modo del cliente, etc.

Nota: endpoints públicos a propósito — el objetivo es que cualquiera pueda
auditar los datos certificados. La transparencia verificable es el punto.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import timezone

from app.core.database import supabase_admin
from app.core.air_quality import get_certified_readings, ESTACIONES
from app.core.blockchain import blockchain
from app.models.air_quality import AirQualityRecord

router = APIRouter(prefix="/air-quality", tags=["air-quality"])

TABLE = "air_quality_readings"


@router.get("/ingest", response_model=list[AirQualityRecord])
def ingest(
    estacion: str = Query("la_flora", description=f"Una de: {list(ESTACIONES.keys())}"),
    limite: int = Query(20, ge=1, le=200),
    anclar: bool = Query(True, description="Anclar hashes on-chain en Ethereum"),
):
    """
    Flujo completo:
    1. Trae lecturas frescas del CKAN (DAGMA Cali).
    2. Clasifica con IQCA oficial (Resolución 2254/2017).
    3. Calcula hash SHA-256 de integridad.
    4. Ancla en Ethereum/HashKey Chain (si BLOCKCHAIN_ENABLED=true).
    5. Guarda en Supabase con upsert por hash (no duplica).
    """
    if estacion not in ESTACIONES:
        raise HTTPException(
            status_code=400,
            detail=f"Estación inválida. Usa una de: {list(ESTACIONES.keys())}",
        )

    # 1. Obtener lecturas certificadas (hash + IQCA ya calculados)
    try:
        records = get_certified_readings(estacion, limite)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar la fuente de datos CKAN: {e}",
        )

    if not records:
        return []

    # 2. Anclaje on-chain en batch (una sola transacción)
    if anclar and blockchain.is_live:
        try:
            batch_payload = [r.model_dump(mode="json") for r in records]
            anchor_result = blockchain.anchor_batch(batch_payload)

            if anchor_result:
                # Aplicar tx_hash, block_number y chain_id a todos los registros del batch
                for record in records:
                    record.tx_hash = anchor_result["tx_hash"]
                    record.block_number = anchor_result["block_number"]
                    record.chain_id = anchor_result["chain_id"]

        except Exception as e:
            # El anclaje falla silenciosamente: guardamos en Supabase de todas formas.
            # Un fallo de blockchain no debe impedir la certificación de datos.
            import logging
            logging.getLogger(__name__).error("Error en anclaje on-chain: %s", e)

    # 3. Persistir en Supabase (upsert por sha256_hash → sin duplicados)
    payload = [r.model_dump(mode="json", exclude={"id"}) for r in records]
    result = supabase_admin.table(TABLE).upsert(payload, on_conflict="sha256_hash").execute()

    return result.data


@router.get("/verify/{sha256_hash}")
def verify_on_chain(sha256_hash: str):
    """
    Verifica on-chain si un hash SHA-256 está certificado en el contrato.

    Útil para que terceros auditen la integridad de un registro:
    recalculan el hash con los datos crudos y consultan este endpoint.
    """
    if len(sha256_hash) != 64:
        raise HTTPException(status_code=400, detail="El hash debe ser un SHA-256 hex de 64 caracteres")

    if not blockchain.is_live:
        return {
            "certified": None,
            "mode": "dry_run",
            "message": "El cliente blockchain está en modo DRY_RUN. Activa BLOCKCHAIN_ENABLED=true para verificar on-chain.",
        }

    try:
        certified = blockchain.is_certified(sha256_hash)
        chain_id = blockchain._w3.eth.chain_id if blockchain._w3 else None
        return {
            "hash": sha256_hash,
            "certified": certified,
            "chain_id": chain_id,
            "contract": blockchain._settings.BLOCKCHAIN_CONTRACT_ADDRESS,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando el contrato: {e}")


@router.get("/stats")
def stats():
    """
    Estadísticas globales del certificador:
    - Total de lecturas en Supabase
    - Total de lecturas certificadas on-chain
    - Modo del cliente blockchain (live / dry_run)
    """
    # Total en Supabase
    try:
        sb_result = supabase_admin.table(TABLE).select("id", count="exact").execute()
        total_db = sb_result.count
    except Exception:
        total_db = None

    # Total on-chain
    total_onchain = blockchain.total_certified()

    return {
        "total_in_database": total_db,
        "total_certified_onchain": total_onchain,
        "blockchain_mode": "live" if blockchain.is_live else "dry_run",
        "blockchain_rpc": blockchain._settings.BLOCKCHAIN_RPC_URL if blockchain.is_live else None,
        "contract_address": blockchain._settings.BLOCKCHAIN_CONTRACT_ADDRESS if blockchain.is_live else None,
        "iqca_norm": "Resolución 2254/2017 - MADS Colombia",
    }


@router.get("/", response_model=list[AirQualityRecord])
def list_certified(
    estacion: str | None = Query(None, description="Filtrar por estación"),
    categoria: str | None = Query(None, description="Filtrar por categoría IQCA (ej. 'Buena', 'Aceptable')"),
    limite: int = Query(50, ge=1, le=500),
):
    """Lista lecturas certificadas guardadas en Supabase, con filtros opcionales."""
    query = (
        supabase_admin.table(TABLE)
        .select("*")
        .order("recorded_at", desc=True)
        .limit(limite)
    )
    if estacion:
        query = query.eq("station", estacion)
    if categoria:
        query = query.eq("iqca_category", categoria)

    result = query.execute()
    return result.data
