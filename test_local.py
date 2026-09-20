"""
test_local.py — Verifica que el backend arranca y responde correctamente.

Uso:
    # Asegúrate de tener el servidor corriendo primero:
    #   uvicorn app.main:app --reload
    #
    # Luego, en otra terminal:
    python test_local.py

Qué verifica:
    1. GET /              → el backend responde
    2. GET /health        → health check retorna {"status": "ok"}
    3. GET /air-quality/stats   → estadísticas (Supabase + blockchain)
    4. GET /air-quality/?limite=2 → lista las primeras 2 lecturas de Supabase
    5. GET /air-quality/ingest?estacion=la_flora&limite=3&anclar=false
             → trae 3 lecturas del DAGMA Cali (sin anclar on-chain)
"""

import sys
import json
import requests

BASE_URL = "http://localhost:8000"
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"

passed = 0
failed = 0


def check(name: str, response: requests.Response, expected_status: int = 200):
    global passed, failed
    ok = response.status_code == expected_status
    status = f"{GREEN}✅  PASS{RESET}" if ok else f"{RED}❌  FAIL{RESET}"
    print(f"  {status}  {name}  [{response.status_code}]")
    if not ok:
        print(f"        Respuesta: {response.text[:300]}")
        failed += 1
    else:
        passed += 1
    return ok


def pretty(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)[:500]


def main():
    global passed, failed

    print(f"\n{BOLD}══════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  Tests locales — Certificador de Calidad del Aire{RESET}")
    print(f"{BOLD}══════════════════════════════════════════════════{RESET}")
    print(f"  Base URL: {BASE_URL}\n")

    # ── 1. Raíz ───────────────────────────────────────────────────────────
    print(f"{BOLD}1. Endpoint raíz{RESET}")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=10)
        if check("GET /", r):
            print(f"       {pretty(r.json())}")
    except requests.exceptions.ConnectionError:
        print(f"  {RED}❌  No se pudo conectar a {BASE_URL}{RESET}")
        print("       ¿Está el servidor corriendo?  →  uvicorn app.main:app --reload")
        sys.exit(1)

    # ── 2. Health check ───────────────────────────────────────────────────
    print(f"\n{BOLD}2. Health check{RESET}")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    if check("GET /health", r):
        data = r.json()
        print(f"       {pretty(data)}")
        if data.get("status") != "ok":
            print(f"  {RED}⚠️   El health check no devolvió status=ok{RESET}")

    # ── 3. Stats (Supabase + blockchain) ──────────────────────────────────
    print(f"\n{BOLD}3. Estadísticas del certificador{RESET}")
    r = requests.get(f"{BASE_URL}/air-quality/stats", timeout=15)
    if check("GET /air-quality/stats", r):
        data = r.json()
        print(f"       {pretty(data)}")
        mode = data.get("blockchain_mode", "?")
        total_db = data.get("total_in_database")
        print(f"\n       blockchain_mode   : {mode}")
        print(f"       total_in_database : {total_db}")
        if mode == "dry_run":
            print(f"       ℹ️   Blockchain en DRY_RUN — configura BLOCKCHAIN_ENABLED=true para activar")

    # ── 4. Listar lecturas guardadas ───────────────────────────────────────
    print(f"\n{BOLD}4. Listar lecturas en Supabase{RESET}")
    r = requests.get(f"{BASE_URL}/air-quality/?limite=2", timeout=15)
    if check("GET /air-quality/?limite=2", r):
        data = r.json()
        print(f"       Registros devueltos: {len(data)}")
        if data:
            first = data[0]
            print(f"       Primer registro:")
            print(f"         station      : {first.get('station')}")
            print(f"         recorded_at  : {first.get('recorded_at')}")
            print(f"         pm10         : {first.get('pm10')}")
            print(f"         iqca_category: {first.get('iqca_category')}")
            print(f"         sha256_hash  : {first.get('sha256_hash', '')[:20]}...")
        else:
            print("       ℹ️   Supabase está vacío. Ejecuta el ingest primero.")

    # ── 5. Ingest (trae datos del DAGMA Cali, sin anclar on-chain) ─────────
    print(f"\n{BOLD}5. Ingest de lecturas frescas del DAGMA Cali{RESET}")
    print("       (puede tardar ~5s mientras consulta datos.cali.gov.co)\n")
    r = requests.get(
        f"{BASE_URL}/air-quality/ingest",
        params={"estacion": "la_flora", "limite": 3, "anclar": "false"},
        timeout=60,
    )
    if check("GET /air-quality/ingest?estacion=la_flora&limite=3&anclar=false", r):
        data = r.json()
        print(f"       Registros ingestados: {len(data)}")
        for rec in data[:2]:
            print(f"         [{rec.get('recorded_at','?')}] "
                  f"PM10={rec.get('pm10','?')} → "
                  f"{rec.get('iqca_category','?')} ({rec.get('iqca_color','?')})")

    # ── Resumen ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}══════════════════════════════════════════════════{RESET}")
    total = passed + failed
    color = GREEN if failed == 0 else RED
    print(f"  {color}{BOLD}Resultado: {passed}/{total} tests pasaron{RESET}")
    print(f"{BOLD}══════════════════════════════════════════════════{RESET}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
