/**
 * Mumbai Testnet Deployment Script
 * Deploys CVTToken, CVTStaking, CVTGovernance to Polygon Mumbai (Chain ID: 80001)
 * 
 * Usage:
 *   npx hardhat run scripts/deploy-mumbai.js --network mumbai
 * 
 * Prerequisites:
 *   - PRIVATE_KEY in .env (deployer account with 0.1+ MATIC)
 *   - MUMBAI_RPC_URL in .env (optional, defaults to public RPC)
 *   - Polygon Mumbai faucet: https://faucet.polygon.technology/
 * 
 * Expected Output: Deployment addresses + contract verification instructions
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

// Configuration
const INITIAL_SUPPLY = ethers.parseEther("100000000"); // 100M CVT
const STAKING_RATE = 1000; // 10% base APY (10 * 100 = 1000 basis points)
const VOTING_DELAY = 1; // 1 block
const VOTING_PERIOD = 45818; // ~1 week
const PROPOSAL_THRESHOLD = ethers.parseEther("1000"); // 1000 CVT to propose

async function main() {
  console.log("\n🚀 MUMBAI TESTNET DEPLOYMENT - CyberViser Web3 Infrastructure\n");
  console.log("=" .repeat(70));

  // Step 1: Get deployer account
  const [deployer] = await ethers.getSigners();
  console.log(`\n📍 Deployer Account: ${deployer.address}`);

  // Get account balance
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`💰 Account Balance: ${ethers.formatEther(balance)} MATIC`);

  if (balance < ethers.parseEther("0.05")) {
    console.error("\n❌ ERROR: Insufficient MATIC balance!");
    console.error("   Minimum 0.05 MATIC required for deployment.");
    console.error("   Get testnet MATIC from: https://faucet.polygon.technology/");
    process.exit(1);
  }

  console.log("\n✅ Sufficient balance confirmed\n");

  // Step 2: Deploy CVTToken
  console.log("📦 Deploying CVTToken (ERC-20)...");
  const CVTToken = await ethers.getContractFactory("CyberViserToken");
  const cvtToken = await CVTToken.deploy();
  await cvtToken.deploymentTransaction().wait();
  console.log(`✅ CVTToken deployed: ${cvtToken.target}`);

  // Verify initial supply
  const totalSupply = await cvtToken.totalSupply();
  console.log(`   Total Supply: ${ethers.formatEther(totalSupply)} CVT`);

  // Step 3: Deploy CVTStaking
  console.log("\n📦 Deploying CVTStaking...");
  const CVTStaking = await ethers.getContractFactory("CVTStaking");
  const cvtStaking = await CVTStaking.deploy(cvtToken.target, STAKING_RATE);
  await cvtStaking.deploymentTransaction().wait();
  console.log(`✅ CVTStaking deployed: ${cvtStaking.target}`);
  console.log(`   Base APY: ${STAKING_RATE / 100}%`);

  // Step 4: Deploy CVTGovernance
  console.log("\n📦 Deploying CVTGovernance...");
  const CVTGovernance = await ethers.getContractFactory("CVTGovernance");
  const cvtGovernance = await CVTGovernance.deploy(
    cvtToken.target,
    VOTING_DELAY,
    VOTING_PERIOD,
    PROPOSAL_THRESHOLD
  );
  await cvtGovernance.deploymentTransaction().wait();
  console.log(`✅ CVTGovernance deployed: ${cvtGovernance.target}`);
  console.log(`   Voting Period: ${VOTING_PERIOD} blocks (~1 week)`);
  console.log(`   Proposal Threshold: ${ethers.formatEther(PROPOSAL_THRESHOLD)} CVT`);

  // Step 5: Set up initial permissions
  console.log("\n🔧 Setting up contract permissions...");
  
  // Add staking contract as minter (if CVTToken has minter role)
  try {
    const addMinterTx = await cvtToken.addMinter(cvtStaking.target);
    await addMinterTx.wait();
    console.log(`✅ CVTStaking added as minter`);
  } catch (e) {
    console.log(`⚠️  Could not add minter: ${e.message.substring(0, 50)}`);
  }

  // Step 6: Save deployment info
  const deploymentInfo = {
    timestamp: new Date().toISOString(),
    network: "mumbai",
    chainId: 80001,
    deployer: deployer.address,
    contracts: {
      cvtToken: {
        address: cvtToken.target,
        name: "CyberViserToken",
        symbol: "CVT",
        totalSupply: ethers.formatEther(totalSupply),
      },
      cvtStaking: {
        address: cvtStaking.target,
        name: "CVTStaking",
        baseAPY: `${STAKING_RATE / 100}%`,
      },
      cvtGovernance: {
        address: cvtGovernance.target,
        name: "CVTGovernance",
        votingPeriod: VOTING_PERIOD,
      },
    },
    scanUrls: {
      token: `https://mumbai.polygonscan.com/address/${cvtToken.target}`,
      staking: `https://mumbai.polygonscan.com/address/${cvtStaking.target}`,
      governance: `https://mumbai.polygonscan.com/address/${cvtGovernance.target}`,
    },
  };

  const deploymentPath = path.join(__dirname, "../deployments/mumbai.json");
  fs.mkdirSync(path.dirname(deploymentPath), { recursive: true });
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`\n💾 Deployment info saved to: deployments/mumbai.json`);

  // Step 7: Display summary
  console.log("\n" + "=" .repeat(70));
  console.log("✅ DEPLOYMENT COMPLETE - MUMBAI TESTNET");
  console.log("=" .repeat(70));
  console.log(`
📋 CONTRACT ADDRESSES:
   CVTToken (ERC-20):   ${cvtToken.target}
   CVTStaking:          ${cvtStaking.target}
   CVTGovernance:       ${cvtGovernance.target}

🔍 VIEW ON POLYGONSCAN:
   CVTToken:    ${deploymentInfo.scanUrls.token}
   CVTStaking:  ${deploymentInfo.scanUrls.staking}
   CVTGovernance: ${deploymentInfo.scanUrls.governance}

📝 NEXT STEPS:
   1. Verify contracts on PolygonScan:
      npx hardhat verify --network mumbai <CONTRACT_ADDRESS>
   
   2. Test portal integration:
      npm test -- --grep "mumbai"
   
   3. Transfer tokens to staking pool:
      npx hardhat run scripts/fund-staking.js --network mumbai
   
   4. Deploy to mainnet:
      npx hardhat run scripts/deploy-polygon.js --network polygon

⚠️  IMPORTANT SECURITY NOTES:
   - Save deployment info in secure location
   - Do NOT commit .env file to repository
   - Contracts are mutable - use timelock for production
   - Request security audit before mainnet deployment

💧 GET MORE TESTNET MATIC:
   https://faucet.polygon.technology/

📚 DOCUMENTATION:
   - Polygon Docs: https://docs.polygon.technology/
   - Hardhat Guide: https://hardhat.org/hardhat-runner/docs/
   - PolygonScan: https://mumbai.polygonscan.com/
  `);

  console.log("\n🍑 Deployment by HancockForge / CyberViser Web3");
  console.log("📍 Testnet: Polygon Mumbai (Chain ID 80001)");
  console.log("🚀 Status: Ready for Web3 portal testing\n");

  return deploymentInfo;
}

main().catch((error) => {
  console.error("\n❌ DEPLOYMENT FAILED:");
  console.error(error.message);
  process.exit(1);
});
