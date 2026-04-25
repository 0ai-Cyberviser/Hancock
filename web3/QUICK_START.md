# ⚡ WEB3 QUICK START GUIDE

**Get your CyberViser Web3 infrastructure running in under 10 minutes**

---

## 🎯 TL;DR - Copy/Paste Commands

```bash
# 1. Install dependencies
cd /home/_0ai_/Hancock-1/web3
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env with your PRIVATE_KEY and POLYGONSCAN_API_KEY

# 3. Get testnet MATIC
# Visit: https://faucet.polygon.technology/
# Select Mumbai, paste your wallet address, get 0.5 MATIC

# 4. Deploy to testnet
npm run deploy:mumbai

# 5. Save contract addresses (printed in output)

# 6. Update frontend
# Edit docs/web3/index.html lines 850-852 with your contract addresses

# 7. Test locally
cd ../docs/web3
python3 -m http.server 8080
# Open http://localhost:8080

# 8. Connect MetaMask and test all features!
```

---

## 📋 What You Need (Before You Start)

1. **Node.js v16+** - `node --version`
2. **MetaMask** - https://metamask.io
3. **Private Key** - From MetaMask (Settings → Security → Reveal Private Key)
4. **PolygonScan API Key** - https://polygonscan.com/apis (free)
5. **Testnet MATIC** - https://faucet.polygon.technology/ (free)

---

## 🚀 Step-by-Step (Beginners)

### Step 1: Install Dependencies (2 minutes)

```bash
cd /home/_0ai_/Hancock-1/web3
npm install
```

Wait for packages to install. You should see:
```
added 500+ packages in 1m
```

### Step 2: Create .env File (3 minutes)

```bash
cp .env.example .env
nano .env  # or vim, vi, any text editor
```

Fill in (get from MetaMask and PolygonScan):
```bash
PRIVATE_KEY=your_private_key_without_0x_prefix
MUMBAI_RPC_URL=https://rpc-mumbai.maticvigil.com
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGONSCAN_API_KEY=your_api_key_here
```

Save and exit (Ctrl+X, Y, Enter if using nano).

**⚠️ NEVER commit .env to Git!**

### Step 3: Get Testnet MATIC (2 minutes)

1. Go to: https://faucet.polygon.technology/
2. Select "Mumbai" network
3. Paste your wallet address
4. Click "Submit"
5. Wait ~30 seconds
6. Check MetaMask - you should have 0.5 MATIC

### Step 4: Deploy Contracts (2 minutes)

```bash
npm run deploy:mumbai
```

Watch the magic happen:
```
🚀 Deploying CyberViser Web3 Infrastructure...
✅ CVTToken deployed to: 0x1234...5678
✅ CVTStaking deployed to: 0xabcd...ef01
✅ CVTGovernance deployed to: 0x9876...5432
🎉 DEPLOYMENT COMPLETE!
```

**SAVE THESE ADDRESSES!**

### Step 5: Update Frontend (1 minute)

```bash
cd ../docs/web3
nano index.html  # or any editor
```

Find lines ~850-852 and replace:
```javascript
const CVT_TOKEN_ADDRESS = '0x1234...5678';  // Your CVTToken address
const STAKING_ADDRESS = '0xabcd...ef01';    // Your CVTStaking address
const GOVERNANCE_ADDRESS = '0x9876...5432'; // Your CVTGovernance address
```

Save and exit.

### Step 6: Test Locally (30 seconds)

```bash
python3 -m http.server 8080
```

Open browser: **http://localhost:8080**

### Step 7: Connect & Test (5 minutes)

1. Click "Connect Wallet"
2. Approve in MetaMask
3. Switch to Mumbai network if prompted
4. Your balance should appear

**Test Token Transfer:**
- Dashboard tab → Send CVT
- Enter another address
- Send 10 CVT
- Approve in MetaMask
- Wait for confirmation

**Test Staking:**
- Staking tab → Enter 100 CVT
- Click "Stake"
- Approve CVT spending
- Confirm staking transaction
- Check "Your Staked" updates

**Test Governance:**
- Governance tab → Create proposal
- Fill in title and description
- Click "Create Proposal"
- Confirm transaction

**Test Mining:**
- Mining tab → Click toggle
- Watch hashrate increase
- Stop mining

---

## 🐛 Common Issues

### "npm install fails"
```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### "Deployment fails - insufficient funds"
```bash
# Get more testnet MATIC
# Visit: https://faucet.polygon.technology/
```

### "MetaMask can't connect"
```bash
# Check network in MetaMask:
# Networks → Add Network → Polygon Mumbai
# Network Name: Mumbai
# RPC URL: https://rpc-mumbai.maticvigil.com
# Chain ID: 80001
# Currency: MATIC
# Block Explorer: https://mumbai.polygonscan.com
```

### "Contract addresses not working"
```bash
# Double-check addresses in index.html
# Make sure you copied from deployment output
# No spaces, starts with 0x
```

---

## 📱 MetaMask Setup for Mumbai

If MetaMask doesn't have Mumbai:

1. Click network dropdown (top)
2. Click "Add Network"
3. Fill in:
   - **Network Name:** Mumbai
   - **RPC URL:** https://rpc-mumbai.maticvigil.com
   - **Chain ID:** 80001
   - **Currency Symbol:** MATIC
   - **Block Explorer:** https://mumbai.polygonscan.com
4. Click "Save"
5. Switch to Mumbai network

---

## 📊 Verify Everything Works

### ✅ Checklist

- [ ] Contracts deployed to Mumbai
- [ ] Contracts verified on PolygonScan
- [ ] Frontend shows wallet address
- [ ] CVT balance displays correctly
- [ ] Can send CVT to another address
- [ ] Can stake CVT (100+ tokens)
- [ ] Pending rewards appear after staking
- [ ] Can claim rewards
- [ ] Can create governance proposal
- [ ] Can vote on proposals
- [ ] Mining toggle works

If all checked ✅ - **YOU'RE READY FOR MAINNET!**

---

## 🚀 Deploy to Mainnet (When Ready)

**⚠️ WARNING: Mainnet costs real money! Test thoroughly first.**

```bash
# Get mainnet MATIC (buy on exchange)
# Transfer ~0.1 MATIC to deployment wallet

# Deploy to Polygon mainnet
cd /home/_0ai_/Hancock-1/web3
npm run deploy:polygon

# Verify contracts
npm run verify:polygon

# Update frontend with mainnet addresses
# Update CHAIN_ID to 137
# Update NETWORK_NAME to 'polygon'

# Deploy to production (GitHub Pages / custom domain)
```

---

## 🎓 Learn More

**Smart Contract Development:**
- OpenZeppelin Contracts: https://docs.openzeppelin.com
- Hardhat Documentation: https://hardhat.org/docs
- Solidity by Example: https://solidity-by-example.org

**Web3 Frontend:**
- Ethers.js Docs: https://docs.ethers.org
- MetaMask Docs: https://docs.metamask.io
- Web3 Modal: https://web3modal.com

**Polygon Network:**
- Polygon Docs: https://docs.polygon.technology
- PolygonScan: https://polygonscan.com
- Polygon Faucet: https://faucet.polygon.technology

---

## 💡 Pro Tips

1. **Use Hardhat Console** for quick contract testing:
   ```bash
   npx hardhat console --network mumbai
   > const CVT = await ethers.getContractAt("CyberViserToken", "0x...");
   > await CVT.balanceOf("0x...");
   ```

2. **Check Gas Prices** before deploying:
   ```bash
   # Visit: https://polygonscan.com/gastracker
   # Wait for low gas periods (usually nights/weekends)
   ```

3. **Test on Multiple Wallets**:
   - Create 2-3 test wallets in MetaMask
   - Send CVT between them
   - Test staking from different accounts
   - Test governance voting

4. **Monitor Transactions**:
   - Every transaction has a TxHash
   - View on PolygonScan: https://mumbai.polygonscan.com/tx/0x...
   - Check status, gas used, events emitted

5. **Save Everything**:
   - Contract addresses
   - Deployment TxHashes
   - PolygonScan verification links
   - Private key backup (secure location!)

---

## 🎉 You're Done!

You now have:
- ✅ ERC-20 CVT token deployed
- ✅ Staking contract with rewards
- ✅ DAO governance system
- ✅ Working Web3 portal
- ✅ Full testing environment

**Next Steps:**
1. Test all features thoroughly
2. Get security audit (recommended)
3. Deploy to mainnet
4. Launch marketing campaign
5. Build community
6. Integrate with Hancock ecosystem

---

## 📞 Need Help?

- **GitHub Issues:** https://github.com/cyberviser/Hancock/issues
- **Documentation:** `/home/_0ai_/Hancock-1/web3/DEPLOYMENT_GUIDE.md`
- **Full Guide:** See DEPLOYMENT_GUIDE.md for detailed instructions

---

**Happy Building! 🚀**

Built by HancockForge / 0AI / CyberViser
