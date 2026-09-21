// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AirQualityCertifier
 * @notice Certificador on-chain de lecturas de calidad del aire del DAGMA Cali.
 *
 * Cada lectura de una estación pública es hasheada (SHA-256) off-chain y el hash
 * se registra aquí permanentemente. Cualquier persona puede verificar que un dato
 * ambiental no fue alterado: recalcula el hash con los datos crudos y comprueba
 * que existe en este contrato con la misma estación y timestamp.
 *
 * ── Clasificación IQCA (Resolución 2254 / 2017 – MADS Colombia) ────────────
 * El índice y la categoría se almacenan junto al hash como referencia auditable.
 *
 * ── Compatibilidad ─────────────────────────────────────────────────────────
 * Desplegado en HashKey Chain (chain ID 177 mainnet / 133 testnet).
 * Compatible con cualquier red EVM (Ethereum mainnet, Sepolia, Polygon, etc.).
 */
contract AirQualityCertifier {

    // ── Eventos ────────────────────────────────────────────────────────────
    event ReadingCertified(
        bytes32 indexed dataHash,
        string  indexed station,
        uint256 timestamp,
        uint16  iqcaIndex,
        string  iqcaCategory,
        address certifiedBy
    );

    // ── Estructuras ────────────────────────────────────────────────────────
    struct Certificate {
        string  station;        // identificador de la estación (ej. "la_flora")
        uint256 recordedAt;     // timestamp Unix de la lectura original
        uint256 certifiedAt;    // timestamp Unix del bloque de certificación
        uint16  iqcaIndex;      // valor numérico IQCA (0-500)
        string  iqcaCategory;   // categoría textual ("Buena", "Aceptable", etc.)
        string  iqcaColor;      // color oficial ("Verde", "Amarillo", etc.)
        address certifiedBy;    // dirección que ancló el registro
        bool    exists;         // flag para verificar existencia
    }

    // ── Estado ─────────────────────────────────────────────────────────────
    /// @dev Mapeamos dataHash (bytes32) → Certificate
    mapping(bytes32 => Certificate) public certificates;

    /// @dev Lista ordenada de hashes para paginación off-chain
    bytes32[] public certifiedHashes;

    /// @dev Propietario del contrato (puede pausar en emergencias)
    address public owner;

    /// @dev Pausa de emergencia
    bool public paused;

    // ── Modificadores ──────────────────────────────────────────────────────
    modifier onlyOwner() {
        require(msg.sender == owner, "AQC: solo el propietario");
        _;
    }

    modifier notPaused() {
        require(!paused, "AQC: contrato pausado");
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────────
    constructor() {
        owner = msg.sender;
    }

    // ── Funciones principales ──────────────────────────────────────────────

    /**
     * @notice Certifica una lectura de calidad del aire on-chain.
     * @param dataHash    SHA-256 del registro (calculado off-chain, como bytes32)
     * @param station     Identificador de la estación ("la_flora", "canaveralejo")
     * @param recordedAt  Timestamp Unix de la lectura original
     * @param iqcaIndex   Índice IQCA numérico (0-500)
     * @param iqcaCategory Categoría IQCA ("Buena", "Aceptable", "Dañina a grupos sensibles", etc.)
     * @param iqcaColor   Color IQCA ("Verde", "Amarillo", "Naranja", "Rojo", "Morado", "Marrón")
     *
     * Si el hash ya existe, la transacción revierte — no se sobreescribe
     * un certificado existente, garantizando inmutabilidad.
     */
    function certify(
        bytes32 dataHash,
        string calldata station,
        uint256 recordedAt,
        uint16  iqcaIndex,
        string calldata iqcaCategory,
        string calldata iqcaColor
    ) external notPaused {
        require(!certificates[dataHash].exists, "AQC: hash ya certificado");
        require(bytes(station).length > 0,      "AQC: station requerida");
        require(iqcaIndex <= 500,               "AQC: indice fuera de rango");

        certificates[dataHash] = Certificate({
            station:     station,
            recordedAt:  recordedAt,
            certifiedAt: block.timestamp,
            iqcaIndex:   iqcaIndex,
            iqcaCategory: iqcaCategory,
            iqcaColor:   iqcaColor,
            certifiedBy: msg.sender,
            exists:      true
        });

        certifiedHashes.push(dataHash);

        emit ReadingCertified(
            dataHash,
            station,
            recordedAt,
            iqcaIndex,
            iqcaCategory,
            msg.sender
        );
    }

    /**
     * @notice Certifica múltiples lecturas en una sola transacción (batch).
     *         Útil para el ingeste periódico que trae varias lecturas a la vez.
     *         Lecturas ya certificadas se saltan (no revierten el batch).
     */
    function certifyBatch(
        bytes32[] calldata dataHashes,
        string[]  calldata stations,
        uint256[] calldata recordedAts,
        uint16[]  calldata iqcaIndexes,
        string[]  calldata iqcaCategories,
        string[]  calldata iqcaColors
    ) external notPaused {
        uint256 len = dataHashes.length;
        require(len > 0,                        "AQC: array vacio");
        require(len == stations.length,         "AQC: longitudes inconsistentes");
        require(len == recordedAts.length,      "AQC: longitudes inconsistentes");
        require(len == iqcaIndexes.length,      "AQC: longitudes inconsistentes");
        require(len == iqcaCategories.length,   "AQC: longitudes inconsistentes");
        require(len == iqcaColors.length,       "AQC: longitudes inconsistentes");
        require(len <= 50,                      "AQC: maximo 50 por batch");

        for (uint256 i = 0; i < len; i++) {
            if (certificates[dataHashes[i]].exists) continue; // skip duplicados

            certificates[dataHashes[i]] = Certificate({
                station:      stations[i],
                recordedAt:   recordedAts[i],
                certifiedAt:  block.timestamp,
                iqcaIndex:    iqcaIndexes[i],
                iqcaCategory: iqcaCategories[i],
                iqcaColor:    iqcaColors[i],
                certifiedBy:  msg.sender,
                exists:       true
            });

            certifiedHashes.push(dataHashes[i]);

            emit ReadingCertified(
                dataHashes[i],
                stations[i],
                recordedAts[i],
                iqcaIndexes[i],
                iqcaCategories[i],
                msg.sender
            );
        }
    }

    // ── Funciones de lectura ───────────────────────────────────────────────

    /**
     * @notice Verifica si un hash está certificado y devuelve su certificado.
     * @param dataHash SHA-256 de la lectura (bytes32)
     */
    function getCertificate(bytes32 dataHash)
        external
        view
        returns (Certificate memory)
    {
        require(certificates[dataHash].exists, "AQC: hash no certificado");
        return certificates[dataHash];
    }

    /**
     * @notice Verifica rápidamente si un hash existe.
     */
    function isCertified(bytes32 dataHash) external view returns (bool) {
        return certificates[dataHash].exists;
    }

    /**
     * @notice Total de lecturas certificadas.
     */
    function totalCertified() external view returns (uint256) {
        return certifiedHashes.length;
    }

    /**
     * @notice Paginación: devuelve un slice de hashes certificados.
     * @param offset Inicio del slice
     * @param limit  Cuántos traer (máx 100)
     */
    function getCertifiedHashes(uint256 offset, uint256 limit)
        external
        view
        returns (bytes32[] memory)
    {
        require(limit <= 100, "AQC: maximo 100 por consulta");
        uint256 total = certifiedHashes.length;
        if (offset >= total) return new bytes32[](0);

        uint256 end = offset + limit;
        if (end > total) end = total;
        uint256 size = end - offset;

        bytes32[] memory result = new bytes32[](size);
        for (uint256 i = 0; i < size; i++) {
            result[i] = certifiedHashes[offset + i];
        }
        return result;
    }

    // ── Administración ─────────────────────────────────────────────────────

    /**
     * @notice Pausa el contrato en caso de emergencia (solo propietario).
     */
    function pause() external onlyOwner {
        paused = true;
    }

    /**
     * @notice Reanuda el contrato (solo propietario).
     */
    function unpause() external onlyOwner {
        paused = false;
    }

    /**
     * @notice Transfiere la propiedad del contrato.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AQC: owner no puede ser zero");
        owner = newOwner;
    }
}
