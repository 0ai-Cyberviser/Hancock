/**
 * Local Testnet Deployment Script  
 * Deploys CVTToken, CVTStaking, CVTGovernance to local Hardhat network
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("\n🚀 LOCAL HARDHAT DEPLOYMENT - CyberViser Web3 Infrastructure\n");
  console.log("=" .repeat(70));

  const [deployer] = await ethers.getSigners();
  console.log(`\n📍 Deployer Account: ${deployer.address}`);

  // Deploy CVTToken
  console.log("\n📦 Deploying CyberViserToken (ERC-20)...");
  const CVTToken = await ethers.getContractFactory("CyberViserToken");
  const cvtToken = await CVTToken.deploy();
  await cvtToken.waitForDeployment();
  const tokenAddr = await cvtToken.getAddress();
  console.log(`✅ CyberViserToken deployed: ${tokenAddr}`);

  // Deploy CVTStaking
  console.log("\n📦 Deploying CVTStaking...");
  const CVTStaking = await ethers.getContractFactory("CVTStaking");
  const cvtStaking = await CVTStaking.deploy(tokenAddr);
  await cvtStaking.waitForDeployment();
  const stakingAddr = await cvtStaking.getAddress();
  console.log(`✅ CVTStaking deployed: ${stakingAddr}`);

  // Add Staking as minter
  const addMinterTx = await cvtToken.addMinter(stakingAddr);
  await addMinterTx.wait();
  console.log(`✅ CVTStaking added as minter`);

  // Deploy CVTGovernance
  console.log("\n📦 Deploying CVTGovernance...");
  const CVTGovernance = await ethers.getContractFactory("CVTGovernance");
  const cvtGovernance = await CVTGovernance.deploy(tokenAddr);
  await cvtGovernance.waitForDeployment();
  const governanceAddr = await cvtGovernance.getAddress();
  console.log(`✅ CVTGovernance deployed: ${governanceAddr}`);

  // Save deployment addresses
  const deployments = {
    network: "local-hardhat",
    timestamp: new Date().toISOString(),
    deployer: deployer.address,
    contracts: {
      CVTToken: tokenAddr,
      CVTStaking: stakingAddr,
      CVTGovernance: governanceAddr,
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
    path.join(outputDir, "local-hardhat.json"),
    JSON.stringify(deployments, null, 2)
  );

  console.log("\n" + "=" .repeat(70));
  console.log("\n✅ DEPLOYMENT COMPLETE!\n");
  console.log("📋 Deployment Summary:");
  console.log(`   CVTToken:       ${tokenAddr}`);
  console.log(`   CVTStaking:     ${stakingAddr}`);
  console.log(`   CVTGovernance:  ${governanceAddr}`);
  console.log(`\n📁 Saved to: deployments/local-hardhat.json`);
  console.log("\n🎉 Ready for testing & integration!\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
