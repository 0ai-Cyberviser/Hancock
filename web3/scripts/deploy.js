const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying CyberViser Web3 Infrastructure...\n");
  
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString(), "\n");
  
  // 1. Deploy CVT Token
  console.log("📝 Deploying CVTToken...");
  const CVTToken = await hre.ethers.getContractFactory("CyberViserToken");
  const cvtToken = await CVTToken.deploy();
  await cvtToken.deployed();
  console.log("✅ CVTToken deployed to:", cvtToken.address);
  console.log("   Initial supply minted: 30,000,000 CVT\n");
  
  // 2. Deploy CVT Staking
  console.log("📝 Deploying CVTStaking...");
  const CVTStaking = await hre.ethers.getContractFactory("CVTStaking");
  const cvtStaking = await CVTStaking.deploy(cvtToken.address);
  await cvtStaking.deployed();
  console.log("✅ CVTStaking deployed to:", cvtStaking.address);
  console.log("   APY: 10% base rate (12.5% early staker bonus for 30 days)\n");
  
  // 3. Deploy CVT Governance
  console.log("📝 Deploying CVTGovernance...");
  const CVTGovernance = await hre.ethers.getContractFactory("CVTGovernance");
  const cvtGovernance = await CVTGovernance.deploy(cvtToken.address);
  await cvtGovernance.deployed();
  console.log("✅ CVTGovernance deployed to:", cvtGovernance.address);
  console.log("   Voting period: 7 days, Quorum: 10%, Timelock: 2 days\n");
  
  // 4. Grant minter role to staking contract (for rewards)
  console.log("🔑 Granting minter role to CVTStaking...");
  const addMinterTx = await cvtToken.addMinter(cvtStaking.address);
  await addMinterTx.wait();
  console.log("✅ CVTStaking can now mint rewards\n");
  
  // 5. Transfer initial tokens to treasury/ecosystem wallets (optional)
  // Uncomment and add addresses when ready for production
  /*
  const TREASURY_ADDRESS = "0x...";
  const ECOSYSTEM_ADDRESS = "0x...";
  const COMMUNITY_ADDRESS = "0x...";
  
  console.log("📦 Distributing tokens...");
  await cvtToken.transfer(TREASURY_ADDRESS, hre.ethers.utils.parseEther("10000000")); // 10M to treasury
  await cvtToken.transfer(ECOSYSTEM_ADDRESS, hre.ethers.utils.parseEther("15000000")); // 15M to ecosystem
  await cvtToken.transfer(COMMUNITY_ADDRESS, hre.ethers.utils.parseEther("25000000")); // 25M to community
  console.log("✅ Token distribution complete\n");
  */
  
  // Summary
  console.log("═══════════════════════════════════════════════════════");
  console.log("🎉 DEPLOYMENT COMPLETE!");
  console.log("═══════════════════════════════════════════════════════");
  console.log("\n📋 Contract Addresses:");
  console.log("   CVTToken:     ", cvtToken.address);
  console.log("   CVTStaking:   ", cvtStaking.address);
  console.log("   CVTGovernance:", cvtGovernance.address);
  console.log("\n🔧 Next Steps:");
  console.log("1. Verify contracts on PolygonScan:");
  console.log("   npx hardhat verify --network mumbai", cvtToken.address);
  console.log("   npx hardhat verify --network mumbai", cvtStaking.address, cvtToken.address);
  console.log("   npx hardhat verify --network mumbai", cvtGovernance.address, cvtToken.address);
  console.log("\n2. Update frontend with contract addresses");
  console.log("3. Fund staking contract with reward tokens");
  console.log("4. Test all functions on testnet");
  console.log("5. Run security audit before mainnet deployment");
  console.log("\n💾 Save these addresses to .env:");
  console.log(`NEXT_PUBLIC_CVT_TOKEN_ADDRESS=${cvtToken.address}`);
  console.log(`NEXT_PUBLIC_CVT_STAKING_ADDRESS=${cvtStaking.address}`);
  console.log(`NEXT_PUBLIC_CVT_GOVERNANCE_ADDRESS=${cvtGovernance.address}`);
  console.log("═══════════════════════════════════════════════════════\n");
  
  // Save deployment info to file
  const fs = require("fs");
  const deploymentInfo = {
    network: hre.network.name,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      CVTToken: cvtToken.address,
      CVTStaking: cvtStaking.address,
      CVTGovernance: cvtGovernance.address,
    },
  };
  
  const deploymentPath = `./deployments/${hre.network.name}-${Date.now()}.json`;
  fs.mkdirSync("./deployments", { recursive: true });
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("📁 Deployment info saved to:", deploymentPath, "\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
