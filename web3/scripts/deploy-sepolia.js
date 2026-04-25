/**
 * Sepolia Testnet Deployment Script  
 * Deploys CVTToken, CVTStaking, CVTGovernance to Ethereum Sepolia
 * 
 * Usage:
 *   npx hardhat run scripts/deploy-sepolia.js --network sepolia
 * 
 * Prerequisites:
 *   - PRIVATE_KEY in .env (deployer with 0.5+ Sepolia ETH)
 *   - Sepolia faucet: https://www.alchemy.com/faucets/ethereum-sepolia
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");
const ethers = hre.ethers;

const INITIAL_SUPPLY = ethers.parseEther("100000000"); // 100M CVT

async function main() {
  console.log("\n🚀 SEPOLIA TESTNET DEPLOYMENT - CyberViser Web3 Infrastructure\n");
  console.log("=" .repeat(70));

  // Step 1: Get deployer account
  const [deployer] = await ethers.getSigners();
  console.log(`\n📍 Deployer Account: ${deployer.address}`);

  // Get account balance
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`💰 Account Balance: ${ethers.formatEther(balance)} ETH`);

  if (balance < ethers.parseEther("0.1")) {
    console.error("\n❌ ERROR: Insufficient ETH balance!");
    console.error("   Minimum 0.1 ETH required for deployment.");
    console.error("   Get Sepolia ETH from: https://www.alchemy.com/faucets/ethereum-sepolia");
    process.exit(1);
  }

  console.log("\n✅ Sufficient balance confirmed\n");

  // Step 2: Deploy CVTToken
  console.log("📦 Deploying CyberViserToken (ERC-20)...");
  const CVTToken = await ethers.getContractFactory("CyberViserToken");
  const cvtToken = await CVTToken.deploy();
  await cvtToken.waitForDeployment();
  const tokenAddr = await cvtToken.getAddress();
  console.log(`✅ CyberViserToken deployed: ${tokenAddr}`);

  // Verify total supply
  const totalSupply = await cvtToken.totalSupply();
  console.log(`   Total Supply: ${ethers.formatEther(totalSupply)} CVT`);

  // Step 3: Deploy CVTStaking
  console.log("\n📦 Deploying CVTStaking...");
  const CVTStaking = await ethers.getContractFactory("CVTStaking");
  const cvtStaking = await CVTStaking.deploy(tokenAddr);
  await cvtStaking.waitForDeployment();
  const stakingAddr = await cvtStaking.getAddress();
  console.log(`✅ CVTStaking deployed: ${stakingAddr}`);

  // Add Staking as minter
  console.log("   Adding CVTStaking as minter...");
  const addMinterTx = await cvtToken.addMinter(stakingAddr);
  await addMinterTx.wait();
  console.log(`   ✅ CVTStaking added as minter`);

  // Step 4: Deploy CVTGovernance
  console.log("\n📦 Deploying CVTGovernance (DAO)...");
  const CVTGovernance = await ethers.getContractFactory("CVTGovernance");
  const cvtGovernance = await CVTGovernance.deploy(tokenAddr);
  await cvtGovernance.waitForDeployment();
  const governanceAddr = await cvtGovernance.getAddress();
  console.log(`✅ CVTGovernance deployed: ${governanceAddr}`);

  // Add Governance as minter
  console.log("   Adding CVTGovernance as minter...");
  const addGovMinterTx = await cvtToken.addMinter(governanceAddr);
  await addGovMinterTx.wait();
  console.log(`   ✅ CVTGovernance added as minter`);

  // Step 5: Save deployment addresses
  const deployments = {
    network: "sepolia",
    chainId: 11155111,
    timestamp: new Date().toISOString(),
    deployer: deployer.address,
    contracts: {
      CVTToken: tokenAddr,
      CVTStaking: stakingAddr,
      CVTGovernance: governanceAddr,
    },
    verification: {
      tokenExplorer: `https://sepolia.etherscan.io/address/${tokenAddr}`,
      stakingExplorer: `https://sepolia.etherscan.io/address/${stakingAddr}`,
      governanceExplorer: `https://sepolia.etherscan.io/address/${governanceAddr}`,
    },
    links: {
      token: tokenAddr,
      staking: stakingAddr,
      governance: governanceAddr,
    },
  };

  const outputDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(outputDir, "sepolia.json"),
    JSON.stringify(deployments, null, 2)
  );

  // Step 6: Display summary
  console.log("\n" + "=" .repeat(70));
  console.log("\n✅ DEPLOYMENT COMPLETE!\n");
  console.log("📋 Deployment Summary:");
  console.log(`   Network: Sepolia (Chain ID: 11155111)`);
  console.log(`   Deployer: ${deployer.address}`);
  console.log(`\n   CVTToken:       ${tokenAddr}`);
  console.log(`   CVTStaking:     ${stakingAddr}`);
  console.log(`   CVTGovernance:  ${governanceAddr}`);
  
  console.log(`\n🔍 Verify on Etherscan:`);
  console.log(`   Token:      https://sepolia.etherscan.io/address/${tokenAddr}`);
  console.log(`   Staking:    https://sepolia.etherscan.io/address/${stakingAddr}`);
  console.log(`   Governance: https://sepolia.etherscan.io/address/${governanceAddr}`);
  
  console.log(`\n📁 Deployment info saved to: deployments/sepolia.json`);
  console.log(`\n🎉 Ready for testing & integration!\n`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
