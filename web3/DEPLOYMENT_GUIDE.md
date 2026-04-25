# 🚀 WEB3 BLOCKCHAIN DEPLOYMENT GUIDE

**CyberViser Web3 Infrastructure - Complete Deployment Guide**

Built by: HancockForge / 0AI / CyberViser  
Version: 1.0.0  
Date: April 25, 2026

---

## 📋 WHAT YOU'RE DEPLOYING

### Smart Contracts
- ✅ **CVTToken.sol** - ERC-20 token (100M supply, minting, burning, pausing)
- ✅ **CVTStaking.sol** - Stake CVT for 10-12.5% APY rewards
- ✅ **CVTGovernance.sol** - DAO voting and proposal system

### Web Interface
- ✅ **web3/index.html** - Complete Web3 portal (wallet, staking, governance, mining, explorer)

### Infrastructure
- ✅ **Hardhat** - Smart contract development and deployment
- ✅ **Polygon Mumbai** - Testnet for testing
- ✅ **Polygon Mainnet** - Production blockchain

---

## 🎯 PRE-DEPLOYMENT CHECKLIST

### Required Tools
```bash
# 1. Node.js (v16+)
node --version  # Should be v16 or higher

# 2. npm or yarn
npm --version

# 3. MetaMask wallet
# Install from https://metamask.io

# 4. MATIC tokens for gas
# Get testnet MATIC from https://faucet.polygon.technology
# For mainnet, buy MATIC on exchanges
```

### Required Accounts
- [ ] MetaMask wallet created and secured
- [ ] Private key backed up (NEVER share this!)
- [ ] PolygonScan API key (https://polygonscan.com/apis)
- [ ] Testnet MATIC received (~1 MATIC for testing)

---

## 📦 STEP 1: INSTALL DEPENDENCIES

```bash
cd /home/_0ai_/Hancock-1/web3

# Install npm packages
npm install

# Expected packages:
# - hardhat (^2.17.0)
# - @openzeppelin/contracts (^5.0.0)
# - @nomicfoundation/hardhat-toolbox (^3.0.0)
# - ethers (^6.7.1)
# - dotenv (^16.3.1)
```

---

## 🔑 STEP 2: CONFIGURE ENVIRONMENT

Create `.env` file:

```bash
cd /home/_0ai_/Hancock-1/web3
cp .env.example .env
vi .env
```

Fill in your credentials:

```bash
# Your deployment wallet private key
PRIVATE_KEY=your_64_character_private_key_here

# Polygon RPC URLs (use defaults or your own)
MUMBAI_RPC_URL=https://rpc-mumbai.maticvigil.com
POLYGON_RPC_URL=https://polygon-rpc.com

# PolygonScan API key for contract verification
POLYGONSCAN_API_KEY=your_polygonscan_api_key_here

# Optional: CoinMarketCap for gas reporting
COINMARKETCAP_API_KEY=your_cmc_api_key_here
```

**⚠️ SECURITY WARNING:**
- NEVER commit `.env` file to Git
- NEVER share your private key
- Use a dedicated deployment wallet (not your main wallet)
- Keep a backup of your private key in a secure location

---

## ✅ STEP 3: COMPILE CONTRACTS

```bash
cd /home/_0ai_/Hancock-1/web3

# Compile smart contracts
npm run compile

# Expected output:
# Compiled 3 Solidity files successfully
# - CVTToken.sol
# - CVTStaking.sol
# - CVTGovernance.sol
```

Check for compilation errors. If successful, you'll see artifacts in `artifacts/` directory.

---

## 🧪 STEP 4: DEPLOY TO TESTNET (Mumbai)

```bash
# Deploy to Polygon Mumbai testnet
npm run deploy:mumbai

# Expected output:
# 🚀 Deploying CyberViser Web3 Infrastructure...
# 
# Deploying contracts with account: 0x...
# Account balance: 1000000000000000000 (1 MATIC)
# 
# 📝 Deploying CVTToken...
# ✅ CVTToken deployed to: 0x...
#    Initial supply minted: 30,000,000 CVT
# 
# 📝 Deploying CVTStaking...
# ✅ CVTStaking deployed to: 0x...
#    APY: 10% base rate (12.5% early staker bonus for 30 days)
# 
# 📝 Deploying CVTGovernance...
# ✅ CVTGovernance deployed to: 0x...
#    Voting period: 7 days, Quorum: 10%, Timelock: 2 days
# 
# 🔑 Granting minter role to CVTStaking...
# ✅ CVTStaking can now mint rewards
# 
# ═══════════════════════════════════════════════════════
# 🎉 DEPLOYMENT COMPLETE!
# ═══════════════════════════════════════════════════════
# 
# 📋 Contract Addresses:
#    CVTToken:      0x1234...5678
#    CVTStaking:    0xabcd...ef01
#    CVTGovernance: 0x9876...5432
```

**Save these addresses!** You'll need them for:
1. Contract verification
2. Frontend configuration
3. Documentation

---

## 🔍 STEP 5: VERIFY CONTRACTS ON POLYGONSCAN

```bash
# Verify CVTToken
npx hardhat verify --network mumbai <CVT_TOKEN_ADDRESS>

# Verify CVTStaking (with constructor arg)
npx hardhat verify --network mumbai <CVT_STAKING_ADDRESS> <CVT_TOKEN_ADDRESS>

# Verify CVTGovernance (with constructor arg)
npx hardhat verify --network mumbai <CVT_GOVERNANCE_ADDRESS> <CVT_TOKEN_ADDRESS>

# Expected output:
# Successfully submitted source code for contract verification
# https://mumbai.polygonscan.com/address/0x.../contracts
```

Benefits of verification:
- ✅ Users can read contract code
- ✅ Increased trust and transparency
- ✅ Easier debugging
- ✅ PolygonScan UI for contract interaction

---

## 🌐 STEP 6: CONFIGURE FRONTEND

Update `docs/web3/index.html` with deployed contract addresses:

```javascript
// Find these lines (around line 850):
const CVT_TOKEN_ADDRESS = 'YOUR_CVT_TOKEN_ADDRESS';
const STAKING_ADDRESS = 'YOUR_STAKING_ADDRESS';
const GOVERNANCE_ADDRESS = 'YOUR_GOVERNANCE_ADDRESS';

// Replace with your deployed addresses:
const CVT_TOKEN_ADDRESS = '0x1234...5678';  // From deployment output
const STAKING_ADDRESS = '0xabcd...ef01';
const GOVERNANCE_ADDRESS = '0x9876...5432';
```

Update network configuration:

```javascript
// For Mumbai testnet (line ~900):
const CHAIN_ID = 80001;
const NETWORK_NAME = 'mumbai';
const EXPLORER_URL = 'https://mumbai.polygonscan.com';

// For Polygon mainnet (when ready):
const CHAIN_ID = 137;
const NETWORK_NAME = 'polygon';
const EXPLORER_URL = 'https://polygonscan.com';
```

---

## 🧪 STEP 7: TEST ON TESTNET

### 7.1 Open Web Portal

```bash
# Serve the website locally
cd /home/_0ai_/Hancock-1/docs/web3
python3 -m http.server 8080

# Open in browser:
# http://localhost:8080
```

### 7.2 Connect MetaMask

1. Click "Connect Wallet" button
2. Approve connection in MetaMask
3. Switch to Polygon Mumbai network in MetaMask
4. Your wallet address and balance should appear

### 7.3 Test Token Functions

**Get Test CVT Tokens:**
```bash
# Option 1: Transfer from deployment wallet
# Open MetaMask, send CVT from deployer address to your test address

# Option 2: Use Hardhat console
npx hardhat console --network mumbai

> const CVT = await ethers.getContractAt("CyberViserToken", "0x...");
> await CVT.transfer("YOUR_TEST_ADDRESS", ethers.utils.parseEther("1000"));
```

**Test Send CVT:**
1. Enter recipient address in "Send CVT" form
2. Enter amount (e.g., 10 CVT)
3. Click "Send CVT"
4. Approve transaction in MetaMask
5. Wait for confirmation
6. Check balance updated

### 7.4 Test Staking

**Stake CVT:**
1. Go to "Staking" tab
2. Enter amount >= 100 CVT
3. Click "Stake"
4. Approve CVT spending (first time)
5. Confirm staking transaction
6. Check "Your Staked" updates

**Check Rewards:**
1. Wait a few minutes
2. Refresh page
3. "Pending Rewards" should increase
4. Click "Claim Rewards"
5. Confirm transaction
6. Check balance increased

**Unstake:**
1. Enter amount to unstake
2. Click "Unstake"
3. Confirm transaction
4. Rewards claimed automatically

### 7.5 Test Governance

**Create Proposal:**
1. Go to "Governance" tab
2. Ensure you have >= 10,000 CVT
3. Fill in proposal details
4. Click "Create Proposal"
5. Confirm transaction
6. Check proposal appears in list

**Vote on Proposal:**
1. Find active proposal
2. Click "Vote For" or "Vote Against"
3. Confirm transaction
4. Check vote count updates

### 7.6 Test Mining (Simulated)

1. Go to "Mining" tab
2. Click toggle switch to start mining
3. Check hashrate updates
4. Check "Mined Today" increases
5. Adjust thread count in settings
6. Click toggle to stop mining

**Note:** Testnet mining is simulated. Production mining requires backend pool.

---

## 🚀 STEP 8: DEPLOY TO MAINNET

**⚠️ CRITICAL: Only deploy to mainnet after thorough testing!**

### Pre-Mainnet Checklist
- [ ] All testnet tests passed
- [ ] Security audit completed (recommended for production)
- [ ] Smart contracts reviewed by at least 2 developers
- [ ] Gas costs calculated and budgeted
- [ ] Mainnet MATIC acquired for deployment (~0.1 MATIC)
- [ ] Deployment wallet funded
- [ ] Emergency pause mechanism tested
- [ ] Team roles and multisig setup (if applicable)

### Deploy to Mainnet

```bash
cd /home/_0ai_/Hancock-1/web3

# Deploy to Polygon mainnet
npm run deploy:polygon

# Verify contracts
npx hardhat verify --network polygon <CVT_TOKEN_ADDRESS>
npx hardhat verify --network polygon <CVT_STAKING_ADDRESS> <CVT_TOKEN_ADDRESS>
npx hardhat verify --network polygon <CVT_GOVERNANCE_ADDRESS> <CVT_TOKEN_ADDRESS>
```

### Update Frontend for Mainnet

```javascript
// docs/web3/index.html
const CVT_TOKEN_ADDRESS = '0x...';  // Mainnet address
const STAKING_ADDRESS = '0x...';
const GOVERNANCE_ADDRESS = '0x...';
const CHAIN_ID = 137;  // Polygon mainnet
const NETWORK_NAME = 'polygon';
const EXPLORER_URL = 'https://polygonscan.com';
```

---

## 🌐 STEP 9: DEPLOY WEB PORTAL

### Option A: GitHub Pages (Recommended for MVP)

```bash
# 1. Copy web3 portal to docs/
cp -r /home/_0ai_/Hancock-1/docs/web3 /home/_0ai_/Hancock-1/docs/

# 2. Commit and push
cd /home/_0ai_/Hancock-1
git add docs/web3/
git commit -m "feat: Add Web3 portal with CVT token, staking, governance"
git push origin main

# 3. Enable GitHub Pages
# Go to: https://github.com/cyberviser/Hancock/settings/pages
# Source: main branch, /docs folder
# Custom domain (optional): web3.cyberviserai.com

# 4. Access portal
# URL: https://cyberviser.github.io/Hancock/web3/
# Or: https://web3.cyberviserai.com (after DNS setup)
```

### Option B: Custom Domain (cyberviserai.com)

```bash
# 1. Build static site
# (Already done - docs/web3/index.html is static HTML)

# 2. Upload to hosting provider
# Options:
# - Vercel: vercel deploy docs/web3
# - Netlify: netlify deploy --dir=docs/web3
# - AWS S3 + CloudFront
# - Traditional web hosting (Apache/Nginx)

# 3. Configure DNS
# A record: @ -> your_server_ip
# CNAME: www -> your_server_domain
# For GitHub Pages: CNAME -> cyberviser.github.io

# 4. Enable HTTPS
# Use Let's Encrypt (free) or your hosting provider's SSL
```

### Option C: IPFS (Decentralized Hosting)

```bash
# Install IPFS
npm install -g ipfs

# Add site to IPFS
ipfs add -r docs/web3/

# Pin to IPFS network
ipfs pin add <hash>

# Access via:
# https://ipfs.io/ipfs/<hash>
# Or: https://web3.cyberviserai.com (with ENS/DNS link)
```

---

## 🔧 STEP 10: POST-DEPLOYMENT SETUP

### 10.1 Fund Staking Contract with Rewards

```bash
# Transfer CVT tokens to staking contract for rewards
npx hardhat console --network polygon

> const CVT = await ethers.getContractAt("CyberViserToken", "<TOKEN_ADDRESS>");
> await CVT.transfer("<STAKING_ADDRESS>", ethers.utils.parseEther("25000000")); // 25M CVT for community rewards
```

### 10.2 Configure Token Distribution

```javascript
// Distribute tokens according to tokenomics:
// - Team: 20M CVT (vesting)
// - Dev Fund: 10M CVT (already minted to deployer)
// - Community: 25M CVT (transferred to staking)
// - Ecosystem: 15M CVT
// - Public Sale: 10M CVT
// - Treasury: 10M CVT
// - Marketing: 5M CVT

// Example transfers:
await CVT.transfer(TREASURY_ADDRESS, ethers.utils.parseEther("10000000"));
await CVT.transfer(ECOSYSTEM_ADDRESS, ethers.utils.parseEther("15000000"));
// etc.
```

### 10.3 Set Up Monitoring

**Track Contract Events:**
```bash
# Monitor CVTToken transfers
npx hardhat run scripts/monitor-transfers.js --network polygon

# Monitor staking events
npx hardhat run scripts/monitor-staking.js --network polygon

# Monitor governance proposals
npx hardhat run scripts/monitor-governance.js --network polygon
```

**Set Up Alerts:**
- Large transfers (> 100K CVT)
- High staking/unstaking volume
- Governance proposals
- Contract pauses
- Security events

### 10.4 Create Liquidity Pool (Optional)

For trading CVT on DEXs:

```bash
# QuickSwap (Polygon DEX)
# 1. Go to https://quickswap.exchange
# 2. Add liquidity: CVT/MATIC pair
# 3. Recommended: 10% of supply (10M CVT)
# 4. Set initial price (e.g., 1 CVT = 0.01 MATIC)
```

---

## 📊 STEP 11: MONITORING & MAINTENANCE

### Daily Monitoring

**Check Dashboard:**
- [ ] Total staked amount
- [ ] Number of stakers
- [ ] Governance proposals
- [ ] Token transfers
- [ ] Contract health

**PolygonScan:**
- [ ] Contract verification status
- [ ] Recent transactions
- [ ] Gas usage
- [ ] Event logs

### Weekly Tasks

- [ ] Review governance proposals
- [ ] Check staking rewards distribution
- [ ] Monitor token holder distribution
- [ ] Review security alerts
- [ ] Update documentation

### Monthly Tasks

- [ ] Security audit (automated)
- [ ] Gas optimization review
- [ ] Community feedback analysis
- [ ] Tokenomics health check
- [ ] Smart contract upgrades (if needed)

---

## 🐛 TROUBLESHOOTING

### Issue: Deployment Fails

**Error:** "Insufficient funds"
- **Solution:** Add more MATIC to deployment wallet

**Error:** "Contract too large"
- **Solution:** Enable optimizer in hardhat.config.js (already enabled)

**Error:** "Network timeout"
- **Solution:** Use different RPC URL or increase timeout

### Issue: Verification Fails

**Error:** "Already verified"
- **Solution:** Contract is already verified, skip this step

**Error:** "Constructor arguments missing"
- **Solution:** Include constructor args in verify command

### Issue: Frontend Not Connecting

**Error:** "MetaMask not detected"
- **Solution:** Install MetaMask extension

**Error:** "Wrong network"
- **Solution:** Switch MetaMask to Polygon network

**Error:** "Contract not found"
- **Solution:** Update contract addresses in index.html

### Issue: Transactions Failing

**Error:** "Insufficient CVT"
- **Solution:** Check balance, get more CVT

**Error:** "Gas estimation failed"
- **Solution:** Increase gas limit or check contract state

**Error:** "Nonce too low"
- **Solution:** Reset MetaMask account (Settings -> Advanced -> Reset Account)

---

## 🔒 SECURITY BEST PRACTICES

### Smart Contract Security

1. **Pause Mechanism**
   - Use `pause()` in emergency
   - Only owner can pause/unpause
   - Test pause functionality regularly

2. **Access Control**
   - Keep owner key secure (hardware wallet recommended)
   - Consider multisig for owner role
   - Grant minter role only to trusted contracts

3. **Rate Limiting**
   - Monitor large transactions
   - Implement cooldown periods for unstaking (if needed)
   - Set maximum transaction sizes

4. **Auditing**
   - Get professional security audit before mainnet
   - Use automated tools: Slither, Mythril, Echidna
   - Bug bounty program (e.g., Immunefi)

### Operational Security

1. **Private Keys**
   - Never commit to Git
   - Use hardware wallets for production
   - Implement multisig for critical operations
   - Rotate keys periodically

2. **Monitoring**
   - Set up 24/7 monitoring
   - Alert on suspicious activities
   - Log all contract interactions
   - Regular security scans

3. **Incident Response**
   - Have emergency response plan
   - Know how to pause contracts
   - Prepare communication templates
   - Test incident procedures

---

## 📈 SUCCESS METRICS

### Launch Week
- [ ] 100+ unique wallet connections
- [ ] 10,000+ CVT staked
- [ ] 5+ governance proposals
- [ ] Zero security incidents
- [ ] 100+ community members

### First Month
- [ ] 1,000+ unique wallets
- [ ] 100,000+ CVT staked
- [ ] 20+ governance proposals
- [ ] Listed on DEX (QuickSwap)
- [ ] 1,000+ community members

### First Quarter
- [ ] 10,000+ unique wallets
- [ ] 10M+ CVT staked (10% of supply)
- [ ] 100+ governance proposals executed
- [ ] Integration with Hancock API
- [ ] 10,000+ community members

---

## 🎉 LAUNCH CHECKLIST

**Pre-Launch (T-7 days):**
- [ ] Testnet deployed and tested
- [ ] Security audit completed
- [ ] Documentation complete
- [ ] Community notified
- [ ] Marketing materials prepared

**Launch Day (T-0):**
- [ ] Mainnet deployment
- [ ] Contract verification
- [ ] Frontend deployment
- [ ] Liquidity pool created
- [ ] Social media announcement
- [ ] Blog post published
- [ ] Monitor closely (24/7)

**Post-Launch (T+1 week):**
- [ ] Address user feedback
- [ ] Fix any UI/UX issues
- [ ] Monitor gas costs
- [ ] Track adoption metrics
- [ ] Community engagement
- [ ] Plan v1.1 features

---

## 📞 SUPPORT & RESOURCES

**Documentation:**
- Smart Contracts: `/home/_0ai_/Hancock-1/web3/contracts/`
- Deployment Scripts: `/home/_0ai_/Hancock-1/web3/scripts/`
- Frontend: `/home/_0ai_/Hancock-1/docs/web3/`

**Tools:**
- Hardhat: https://hardhat.org/docs
- OpenZeppelin: https://docs.openzeppelin.com
- Polygon: https://docs.polygon.technology
- Ethers.js: https://docs.ethers.org

**Community:**
- GitHub: https://github.com/cyberviser/Hancock
- Discord: (create server)
- Telegram: (create group)
- Twitter: @cyberviserai

**Emergency Contact:**
- Project Lead: Johnny Watters / 0AI
- Email: contact@cyberviserai.com

---

## 🚀 YOU'RE READY TO LAUNCH!

Follow this guide step-by-step, and you'll have a fully functional Web3 ecosystem with:
- ✅ ERC-20 CVT token on Polygon
- ✅ Staking with 10-12.5% APY
- ✅ DAO governance
- ✅ Browser mining (simulated)
- ✅ Blockchain explorer
- ✅ Professional Web3 portal

**Next Steps:**
1. Deploy to testnet (today)
2. Test thoroughly (1 week)
3. Security audit (2 weeks)
4. Deploy to mainnet (week 4)
5. Launch marketing campaign
6. Grow community
7. Build ecosystem integrations

**Good luck! 🚀**

---

Built by: HancockForge / 0AI / CyberViser  
For support: https://github.com/cyberviser/Hancock/issues  
License: MIT
