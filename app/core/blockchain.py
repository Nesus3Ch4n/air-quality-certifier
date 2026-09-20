"""
Módulo de interacción con el smart contract AirQualityCertifier en Ethereum.

Responsabilidades:
- Conectar al nodo RPC (HashKey Chain por defecto, cualquier EVM configurable).
- Anclar hashes SHA-256 de lecturas de calidad del aire en el contrato.
- Soportar modo DRY_RUN: si no hay wallet configurada, registra el hash en los
  logs pero no envía transacciones reales. Útil para demos y entornos sin wallet.

Notas de seguridad:
- La clave privada NUNCA se loguea ni se devuelve en respuestas HTTP.
- Usa variables de entorno; nunca hardcodes.
- Las funciones de escritura esperan que la wallet tenga gas suficiente.
"""
import logging
import json
from pathlib import Path
from typing import TypedDict

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ABI mínima del contrato: solo las funciones que usa este módulo.
# Mantenerla aquí evita una dependencia en tiempo de build con Hardhat/Foundry.
_ABI = json.loads("""
[
  {
    "inputs": [
      {"internalType": "bytes32", "name": "dataHash",     "type": "bytes32"},
      {"internalType": "string",  "name": "station",      "type": "string"},
      {"internalType": "uint256", "name": "recordedAt",   "type": "uint256"},
      {"internalType": "uint16",  "name": "iqcaIndex",    "type": "uint16"},
      {"internalType": "string",  "name": "iqcaCategory", "type": "string"},
      {"internalType": "string",  "name": "iqcaColor",    "type": "string"}
    ],
    "name": "certify",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {"internalType": "bytes32[]", "name": "dataHashes",    "type": "bytes32[]"},
      {"internalType": "string[]",  "name": "stations",      "type": "string[]"},
      {"internalType": "uint256[]", "name": "recordedAts",   "type": "uint256[]"},
      {"internalType": "uint16[]",  "name": "iqcaIndexes",   "type": "uint16[]"},
      {"internalType": "string[]",  "name": "iqcaCategories","type": "string[]"},
      {"internalType": "string[]",  "name": "iqcaColors",    "type": "string[]"}
    ],
    "name": "certifyBatch",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "bytes32", "name": "dataHash", "type": "bytes32"}],
    "name": "isCertified",
    "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "totalCertified",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  }
]
""")


class AnchorResult(TypedDict):
    tx_hash: str
    block_number: int
    chain_id: int


class BlockchainClient:
    """
    Cliente para el contrato AirQualityCertifier.

    Si BLOCKCHAIN_ENABLED=false o no hay PRIVATE_KEY configurada, opera en
    modo DRY_RUN: devuelve resultados simulados sin enviar transacciones.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._w3 = None
        self._contract = None
        self._account = None
        self._dry_run = True
        self._init()

    def _init(self) -> None:
        """Inicializa la conexión Web3. Falla silenciosamente si no hay config."""
        settings = self._settings

        if not settings.BLOCKCHAIN_ENABLED:
            logger.info("Blockchain: modo DRY_RUN (BLOCKCHAIN_ENABLED=false)")
            return

        if not settings.BLOCKCHAIN_RPC_URL:
            logger.warning("Blockchain: BLOCKCHAIN_RPC_URL no configurada → DRY_RUN")
            return

        if not settings.BLOCKCHAIN_PRIVATE_KEY:
            logger.warning("Blockchain: BLOCKCHAIN_PRIVATE_KEY no configurada → DRY_RUN")
            return

        if not settings.BLOCKCHAIN_CONTRACT_ADDRESS:
            logger.warning("Blockchain: BLOCKCHAIN_CONTRACT_ADDRESS no configurada → DRY_RUN")
            return

        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware

            w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))

            # HashKey Chain y otras PoA necesitan este middleware
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not w3.is_connected():
                logger.error("Blockchain: no se pudo conectar a %s → DRY_RUN",
                             settings.BLOCKCHAIN_RPC_URL)
                return

            account = w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(settings.BLOCKCHAIN_CONTRACT_ADDRESS),
                abi=_ABI,
            )

            self._w3 = w3
            self._contract = contract
            self._account = account
            self._dry_run = False

            logger.info(
                "Blockchain: conectado a %s | chain_id=%s | wallet=%s | contrato=%s",
                settings.BLOCKCHAIN_RPC_URL,
                w3.eth.chain_id,
                account.address,
                settings.BLOCKCHAIN_CONTRACT_ADDRESS,
            )

        except ImportError:
            logger.error("Blockchain: web3 no instalado → DRY_RUN (pip install web3)")
        except Exception as exc:
            logger.error("Blockchain: error de inicialización → DRY_RUN: %s", exc)

    # ── API pública ────────────────────────────────────────────────────────

    @property
    def is_live(self) -> bool:
        """True si hay conexión real; False si está en DRY_RUN."""
        return not self._dry_run

    def anchor(
        self,
        data_hash_hex: str,
        station: str,
        recorded_at_ts: int,
        iqca_index: int,
        iqca_category: str,
        iqca_color: str,
    ) -> AnchorResult | None:
        """
        Ancla un hash en el contrato.

        Parámetros:
            data_hash_hex   SHA-256 hex del registro (sin 0x)
            station         Identificador de la estación
            recorded_at_ts  Timestamp Unix de la lectura
            iqca_index      Valor numérico IQCA (0-500)
            iqca_category   Categoría textual IQCA
            iqca_color      Color IQCA

        Retorna AnchorResult con tx_hash, block_number, chain_id, o None en DRY_RUN.
        """
        if self._dry_run:
            logger.info("DRY_RUN anchor | hash=%s | station=%s | iqca=%s %s",
                        data_hash_hex[:12], station, iqca_index, iqca_category)
            return None

        return self._send_certify(
            data_hash_hex, station, recorded_at_ts,
            iqca_index, iqca_category, iqca_color,
        )

    def anchor_batch(self, records: list[dict]) -> AnchorResult | None:
        """
        Ancla múltiples registros en una sola transacción.

        Cada elemento de `records` debe tener:
            sha256_hash, station, recorded_at (datetime o timestamp),
            iqca_index, iqca_category, iqca_color
        """
        if self._dry_run:
            logger.info("DRY_RUN anchor_batch | %d registros", len(records))
            return None

        if not records:
            return None

        return self._send_certify_batch(records)

    def is_certified(self, data_hash_hex: str) -> bool:
        """Consulta si un hash ya está certificado en el contrato (lectura, sin gas)."""
        if self._dry_run:
            return False
        try:
            hash_bytes = bytes.fromhex(data_hash_hex)
            return self._contract.functions.isCertified(hash_bytes).call()
        except Exception as exc:
            logger.error("Blockchain: error en isCertified: %s", exc)
            return False

    def total_certified(self) -> int | None:
        """Devuelve el total de lecturas certificadas en el contrato."""
        if self._dry_run:
            return None
        try:
            return self._contract.functions.totalCertified().call()
        except Exception as exc:
            logger.error("Blockchain: error en totalCertified: %s", exc)
            return None

    # ── Internos ───────────────────────────────────────────────────────────

    def _build_and_send(self, fn) -> AnchorResult:
        """Construye, firma y envía una transacción; espera el recibo."""
        w3 = self._w3
        chain_id = w3.eth.chain_id
        nonce = w3.eth.get_transaction_count(self._account.address)

        tx = fn.build_transaction({
            "from":     self._account.address,
            "nonce":    nonce,
            "chainId":  chain_id,
            "gas":      500_000,
            "gasPrice": w3.eth.gas_price,
        })

        signed = self._account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise RuntimeError(f"Transacción revertida: {tx_hash.hex()}")

        result: AnchorResult = {
            "tx_hash":      tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "chain_id":     chain_id,
        }
        logger.info("Blockchain: certificado | tx=%s | bloque=%d | chain=%d",
                    result["tx_hash"][:18], result["block_number"], result["chain_id"])
        return result

    def _send_certify(
        self,
        data_hash_hex: str,
        station: str,
        recorded_at_ts: int,
        iqca_index: int,
        iqca_category: str,
        iqca_color: str,
    ) -> AnchorResult:
        hash_bytes = bytes.fromhex(data_hash_hex)
        fn = self._contract.functions.certify(
            hash_bytes,
            station,
            recorded_at_ts,
            iqca_index,
            iqca_category,
            iqca_color,
        )
        return self._build_and_send(fn)

    def _send_certify_batch(self, records: list[dict]) -> AnchorResult:
        from datetime import datetime

        hashes, stations, timestamps, indexes, categories, colors = [], [], [], [], [], []
        for r in records:
            hashes.append(bytes.fromhex(r["sha256_hash"]))
            stations.append(r["station"])

            rat = r.get("recorded_at")
            if isinstance(rat, datetime):
                ts = int(rat.timestamp())
            elif isinstance(rat, (int, float)):
                ts = int(rat)
            else:
                ts = 0
            timestamps.append(ts)

            indexes.append(int(r.get("iqca_index") or 0))
            categories.append(r.get("iqca_category", ""))
            colors.append(r.get("iqca_color", ""))

        fn = self._contract.functions.certifyBatch(
            hashes, stations, timestamps, indexes, categories, colors
        )
        return self._build_and_send(fn)


# Instancia singleton — se inicializa una vez al importar el módulo.
# Si la configuración cambia, reinicia el proceso.
blockchain = BlockchainClient()
