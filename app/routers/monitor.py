"""
GET /monitor
Endpoint de monitorización: estado de todas las dependencias externas en una sola llamada.
- Supabase: verifica conexión y cuenta registros
- CKAN (DAGMA): verifica que la fuente de datos pública responde
- Blockchain: modo activo o dry_run
"""
import time
import requests
from fastapi import APIRouter
from app.core.database import supabase_admin
from app.core.blockchain import blockchain
from app.core.air_quality import CKAN_BASE_URL, ESTACIONES

router = APIRouter(tags=["monitor"])


def _check_supabase() -> dict:
    t0 = time.monotonic()
    try:
        result = supabase_admin.table("air_quality_readings").select("id", count="exact").execute()
        return {
            "status": "ok",
            "total_records": result.count,
            "latency_ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "latency_ms": round((time.monotonic() - t0) * 1000)}


def _check_ckan() -> dict:
    t0 = time.monotonic()
    try:
        resp = requests.get(
            CKAN_BASE_URL,
            params={"resource_id": ESTACIONES["la_flora"], "limit": 1},
            timeout=8,
        )
        resp.raise_for_status()
        ok = resp.json().get("success", False)
        return {
            "status": "ok" if ok else "error",
            "http_status": resp.status_code,
            "latency_ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "latency_ms": round((time.monotonic() - t0) * 1000)}


def _check_blockchain() -> dict:
    if not blockchain.is_live:
        return {"status": "dry_run", "detail": "BLOCKCHAIN_ENABLED=false"}
    total = blockchain.total_certified()
    return {
        "status": "ok",
        "total_certified": total,
        "rpc": blockchain._settings.BLOCKCHAIN_RPC_URL,
        "contract": blockchain._settings.BLOCKCHAIN_CONTRACT_ADDRESS,
    }


@router.get("/monitor")
def monitor():
    """Estado de todas las dependencias. Útil para dashboards y alertas externas."""
    supabase = _check_supabase()
    ckan = _check_ckan()
    chain = _check_blockchain()

    overall = "ok" if supabase["status"] == "ok" and ckan["status"] == "ok" else "degraded"

    return {
        "overall": overall,
        "services": {
            "supabase": supabase,
            "ckan_dagma": ckan,
            "blockchain": chain,
        },
    }
