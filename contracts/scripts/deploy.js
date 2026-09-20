/**
 * deploy.js — Despliega AirQualityCertifier en la red indicada.
 *
 * Uso:
 *   cd contracts
 *   npm install                                         # primera vez
 *   npx hardhat run scripts/deploy.js --network hashkey_testnet
 *   npx hardhat run scripts/deploy.js --network sepolia
 *   npx hardhat run scripts/deploy.js --network localhost   # nodo local
 *
 * Después del despliegue, el script imprime la dirección del contrato.
 * Cópiala en el .env del backend:
 *   BLOCKCHAIN_CONTRACT_ADDRESS=0x...
 *   BLOCKCHAIN_ENABLED=true
 *   BLOCKCHAIN_PRIVATE_KEY=0x...
 */

const { ethers, network } = require("hardhat");

async function main() {
  console.log("\n══════════════════════════════════════════════════════");
  console.log("  Desplegando AirQualityCertifier");
  console.log(`  Red: ${network.name} (chain ID: ${network.config.chainId ?? "desconocido"})`);
  console.log("══════════════════════════════════════════════════════\n");

  // Obtener la cuenta del desplegador
  const [deployer] = await ethers.getSigners();
  console.log(`  Wallet del desplegador : ${deployer.address}`);

  // Balance de la wallet
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`  Balance               : ${ethers.formatEther(balance)} ETH/HSK`);

  if (balance === 0n) {
    console.error(
      "\n❌  La wallet no tiene saldo. Consigue fondos de prueba antes de desplegar:"
    );
    console.error("   HashKey testnet faucet: https://faucet.hsk.xyz");
    console.error("   Sepolia faucet:         https://sepoliafaucet.com\n");
    process.exit(1);
  }

  // Compilar y obtener la factory del contrato
  console.log("\n  Compilando contrato...");
  const AirQualityCertifier = await ethers.getContractFactory("AirQualityCertifier");

  // Desplegar
  console.log("  Enviando transacción de despliegue...");
  const contract = await AirQualityCertifier.deploy();

  // Esperar confirmación
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();
  const receipt = await deployTx.wait();

  console.log("\n══════════════════════════════════════════════════════");
  console.log("  ✅  DESPLIEGUE EXITOSO");
  console.log("══════════════════════════════════════════════════════");
  console.log(`  Dirección del contrato : ${contractAddress}`);
  console.log(`  Hash de la transacción : ${deployTx.hash}`);
  console.log(`  Bloque                 : ${receipt.blockNumber}`);
  console.log(`  Gas usado              : ${receipt.gasUsed.toString()}`);
  console.log("══════════════════════════════════════════════════════\n");

  // Instrucciones para actualizar el .env
  console.log("  📋  Actualiza tu .env con los siguientes valores:");
  console.log("  ─────────────────────────────────────────────────");
  console.log(`  BLOCKCHAIN_ENABLED=true`);
  console.log(`  BLOCKCHAIN_CONTRACT_ADDRESS=${contractAddress}`);
  console.log(`  BLOCKCHAIN_RPC_URL=${network.config.url ?? ""}`);
  console.log("  ─────────────────────────────────────────────────\n");

  // Explorador de bloques
  const explorers = {
    hashkey_testnet: `https://testnet.hashscan.io/contract/${contractAddress}`,
    hashkey_mainnet: `https://hashscan.io/contract/${contractAddress}`,
    sepolia:         `https://sepolia.etherscan.io/address/${contractAddress}`,
  };
  const explorerUrl = explorers[network.name];
  if (explorerUrl) {
    console.log(`  🔍  Ver en explorador: ${explorerUrl}\n`);
  }

  // Verificación rápida: leer owner y estado inicial del contrato
  console.log("  Verificando contrato desplegado...");
  const owner = await contract.owner();
  const paused = await contract.paused();
  const total = await contract.totalCertified();
  console.log(`  owner           : ${owner}`);
  console.log(`  paused          : ${paused}`);
  console.log(`  totalCertified  : ${total.toString()}`);
  console.log("\n  ✅  El contrato responde correctamente.\n");
}

main().catch((error) => {
  console.error("\n❌  Error durante el despliegue:", error);
  process.exitCode = 1;
});
