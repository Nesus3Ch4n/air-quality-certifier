require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../.env" });

// Lee la clave privada del .env del backend (misma carpeta raíz del proyecto)
const PRIVATE_KEY = process.env.BLOCKCHAIN_PRIVATE_KEY || "";

// Validación mínima para evitar errores confusos al compilar
if (
  PRIVATE_KEY &&
  PRIVATE_KEY !== "0xtuprivatekey" &&
  !PRIVATE_KEY.match(/^(0x)?[0-9a-fA-F]{64}$/)
) {
  console.warn(
    "⚠️  BLOCKCHAIN_PRIVATE_KEY en .env no parece una clave válida (debe ser hex de 64 chars)."
  );
}

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true,
    },
  },

  networks: {
    // ── Red local Hardhat (para pruebas rápidas sin gas real) ──────────────
    localhost: {
      url: "http://127.0.0.1:8545",
    },

    // ── HashKey Chain Testnet (chain ID 133) ──────────────────────────────
    // HSK de prueba: https://faucet.hsk.xyz
    // Explorer:      https://testnet.hashscan.io
    hashkey_testnet: {
      url: "https://hashkeychain-testnet.alt.technology",
      chainId: 133,
      accounts: PRIVATE_KEY ? [PRIVATE_KEY] : [],
    },

    // ── HashKey Chain Mainnet (chain ID 177) ──────────────────────────────
    // Solo usar cuando el contrato esté auditado y probado en testnet.
    hashkey_mainnet: {
      url: "https://mainnet.hsk.xyz",
      chainId: 177,
      accounts: PRIVATE_KEY ? [PRIVATE_KEY] : [],
    },

    // ── Ethereum Sepolia (testnet alternativa) ────────────────────────────
    // ETH de prueba: https://sepoliafaucet.com  o  https://faucet.quicknode.com/ethereum/sepolia
    // Explorer:      https://sepolia.etherscan.io
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "https://ethereum-sepolia.publicnode.com",
      chainId: 11155111,
      accounts: PRIVATE_KEY ? [PRIVATE_KEY] : [],
    },
  },

  // Configuración del gas reporter (opcional, se activa con REPORT_GAS=true)
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
  },
};
