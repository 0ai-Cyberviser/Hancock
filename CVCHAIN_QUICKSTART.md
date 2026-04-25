# CVChain Quick Start Guide
**Your Cosmos SDK Blockchain in 4 Weeks**

---

## 🚀 WEEK 1: ENVIRONMENT SETUP & LEARNING

### Day 1: Development Environment

```bash
# 1. Install Go 1.21+
wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Verify
go version  # Should show go1.21.6

# 2. Install Ignite CLI
curl https://get.ignite.com/cli | bash
# Verify
ignite version  # Should show latest version

# 3. Install Docker (for IPFS and testing)
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in

# 4. Install Node.js (for tooling)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 5. Clone CVChain repository (create first)
mkdir -p ~/cvchain
cd ~/cvchain
git init
```

### Day 2-3: Cosmos SDK Deep Dive

**Study These (in order):**

1. **Introduction to Cosmos** (2 hours)
   - https://docs.cosmos.network/main/intro/overview
   - Understand: Tendermint, ABCI, SDK modules
   
2. **Building Modules** (4 hours)
   - https://docs.cosmos.network/main/building-modules/intro
   - Understand: Keeper, Msg, Query, State

3. **Ignite CLI Tutorial** (3 hours)
   - https://docs.ignite.com/guide
   - Complete: "Build a Blockchain" tutorial

4. **Study Reference: Osmosis x/gamm module** (3 hours)
   - https://github.com/osmosis-labs/osmosis/tree/main/x/gamm
   - See how a complex module is structured

### Day 4-5: Scaffold CVChain

```bash
cd ~/cvchain

# Scaffold the chain
ignite scaffold chain cvchain \
  --address-prefix cv \
  --no-module

cd cvchain

# Initialize git
git add .
git commit -m "Initial CVChain scaffold"

# Create GitHub repository
gh repo create cyberviser/cvchain --public --source=. --remote=origin
git push -u origin main
```

**Configure Chain Parameters:**

Edit `config.yml`:
```yaml
accounts:
  - name: alice
    coins: ["100000000stake", "100000000ucvt"]
  - name: bob
    coins: ["100000000stake", "100000000ucvt"]
validator:
  name: validator1
  staked: "100000000stake"
  
client:
  vuex:
    path: "vue/src/store"
  
faucet:
  name: alice
  coins: ["5ucvt"]
  coins_max: ["100ucvt"]
  
genesis:
  chain_id: "cvchain-1"
  
init:
  home: "$HOME/.cvchain"
```

### Day 6-7: Test Basic Chain

```bash
# Start the chain
ignite chain serve

# In another terminal, test CLI
cvchain query bank balances $(cvchain keys show alice -a)
cvchain tx bank send alice $(cvchain keys show bob -a) 100ucvt --yes
```

**Success Criteria Week 1:**
- ✅ Environment fully set up
- ✅ Cosmos SDK concepts understood
- ✅ Basic CVChain running locally
- ✅ Can send transactions via CLI

---

## 🔧 WEEK 2: X/AUDIT MODULE

### Day 8-9: Module Scaffolding

```bash
cd ~/cvchain/cvchain

# Scaffold the audit module
ignite scaffold module audit

# Add audit message type
ignite scaffold message register-audit \
  contractAddress:string \
  contractChain:string \
  auditorAddress:string \
  reportCID:string \
  securityScore:uint \
  --module audit

# Add query for audit history
ignite scaffold query get-audit \
  contractAddress:string \
  --module audit \
  --response audit

ignite scaffold query list-audits \
  --module audit \
  --response audits
```

### Day 10-11: Module Logic Implementation

Edit `x/audit/keeper/msg_server_register_audit.go`:

```go
package keeper

import (
    "context"
    "crypto/sha256"
    "encoding/hex"
    "fmt"

    sdk "github.com/cosmos/cosmos-sdk/types"
    "cvchain/x/audit/types"
)

func (k msgServer) RegisterAudit(goCtx context.Context, msg *types.MsgRegisterAudit) (*types.MsgRegisterAuditResponse, error) {
    ctx := sdk.UnwrapSDKContext(goCtx)

    // Validate auditor has staked
    // TODO: Check x/reputation module for auditor status
    
    // Create audit record
    audit := types.Audit{
        Id:              generateAuditID(msg),
        ContractAddress: msg.ContractAddress,
        ContractChain:   msg.ContractChain,
        AuditorAddress:  msg.AuditorAddress,
        ReportCID:       msg.ReportCID,
        SecurityScore:   msg.SecurityScore,
        Timestamp:       ctx.BlockTime().Unix(),
        Status:          "completed",
    }

    // Store audit
    k.SetAudit(ctx, audit)

    // Emit event
    ctx.EventManager().EmitEvent(
        sdk.NewEvent(
            types.EventTypeAuditRegistered,
            sdk.NewAttribute(types.AttributeKeyContractAddress, msg.ContractAddress),
            sdk.NewAttribute(types.AttributeKeyAuditor, msg.AuditorAddress),
            sdk.NewAttribute(types.AttributeKeyScore, fmt.Sprintf("%d", msg.SecurityScore)),
        ),
    )

    return &types.MsgRegisterAuditResponse{
        AuditId: audit.Id,
    }, nil
}

func generateAuditID(msg *types.MsgRegisterAudit) string {
    data := fmt.Sprintf("%s:%s:%s", 
        msg.ContractAddress,
        msg.AuditorAddress,
        msg.ReportCID,
    )
    hash := sha256.Sum256([]byte(data))
    return hex.EncodeToString(hash[:])
}
```

### Day 12-13: Add IPFS Integration

```bash
# Install IPFS Go client
cd ~/cvchain/cvchain
go get github.com/ipfs/go-ipfs-api
```

Create `x/audit/keeper/ipfs.go`:

```go
package keeper

import (
    "bytes"
    "fmt"
    
    shell "github.com/ipfs/go-ipfs-api"
)

type IPFSClient struct {
    sh *shell.Shell
}

func NewIPFSClient(url string) *IPFSClient {
    return &IPFSClient{
        sh: shell.NewShell(url),
    }
}

func (c *IPFSClient) UploadAuditReport(report []byte) (string, error) {
    cid, err := c.sh.Add(bytes.NewReader(report))
    if err != nil {
        return "", fmt.Errorf("failed to upload to IPFS: %w", err)
    }
    return cid, nil
}

func (c *IPFSClient) GetAuditReport(cid string) ([]byte, error) {
    reader, err := c.sh.Cat(cid)
    if err != nil {
        return nil, fmt.Errorf("failed to fetch from IPFS: %w", err)
    }
    defer reader.Close()
    
    buf := new(bytes.Buffer)
    _, err = buf.ReadFrom(reader)
    if err != nil {
        return nil, fmt.Errorf("failed to read IPFS data: %w", err)
    }
    
    return buf.Bytes(), nil
}
```

### Day 14: Testing & Documentation

```bash
# Write tests
cd x/audit/keeper
# Edit keeper_test.go

# Run tests
go test ./x/audit/...

# Start chain with audit module
ignite chain serve --reset-once
```

Test audit registration:
```bash
# Register an audit
cvchain tx audit register-audit \
  "0x1234...abcd" \
  "ethereum" \
  $(cvchain keys show alice -a) \
  "QmX...ABC" \
  85 \
  --from alice \
  --yes

# Query audit
cvchain query audit get-audit "0x1234...abcd"
```

**Success Criteria Week 2:**
- ✅ x/audit module operational
- ✅ Can register audits via CLI
- ✅ IPFS integration working
- ✅ Tests passing

---

## 🛡️ WEEK 3: X/SECURITY & X/REPUTATION MODULES

### Day 15-16: Scaffold Security Module

```bash
# Scaffold security module
ignite scaffold module security

# Add security scoring message
ignite scaffold message calculate-score \
  contractAddress:string \
  --module security \
  --response score:uint

# Add vulnerability tracking
ignite scaffold map vulnerability \
  cveId:string \
  severity:string \
  description:string \
  --module security
```

### Day 17-18: Scaffold Reputation Module

```bash
# Scaffold reputation module
ignite scaffold module reputation

# Add auditor staking
ignite scaffold message stake-auditor \
  amount:uint \
  --module reputation

# Add reputation score
ignite scaffold map auditor-reputation \
  auditorAddress:string \
  reputationScore:uint \
  totalAudits:uint \
  successfulAudits:uint \
  --module reputation

# Add slashing
ignite scaffold message slash-auditor \
  auditorAddress:string \
  reason:string \
  --module reputation
```

### Day 19-20: Integration Testing

Create `tests/integration/audit_flow_test.go`:

```go
package integration

import (
    "testing"
    
    sdk "github.com/cosmos/cosmos-sdk/types"
    "github.com/stretchr/testify/require"
)

func TestFullAuditFlow(t *testing.T) {
    // 1. Auditor stakes
    // 2. Registers audit
    // 3. Security score calculated
    // 4. Reputation updated
    // Test implementation
}
```

### Day 21: Module Integration

Edit `app/app.go` to wire all modules together:

```go
// Add keepers
app.AuditKeeper = auditkeeper.NewKeeper(/*...*/)
app.SecurityKeeper = securitykeeper.NewKeeper(/*...*/)
app.ReputationKeeper = reputationkeeper.NewKeeper(/*...*/)

// Set inter-module dependencies
app.AuditKeeper.SetSecurityKeeper(app.SecurityKeeper)
app.AuditKeeper.SetReputationKeeper(app.ReputationKeeper)
```

**Success Criteria Week 3:**
- ✅ All 3 modules integrated
- ✅ Cross-module communication working
- ✅ End-to-end audit flow complete
- ✅ Integration tests passing

---

## 🌐 WEEK 4: TESTNET DEPLOYMENT

### Day 22-23: Infrastructure Setup

```bash
# Use DigitalOcean/Hetzner for cost efficiency
# 5 droplets: 3 validators, 2 full nodes
# 4 vCPU, 8GB RAM, 100GB SSD each

# Setup script for each node
#!/bin/bash
# install-node.sh

# Install Go
wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

# Clone and build CVChain
git clone https://github.com/cyberviser/cvchain
cd cvchain
make install

# Initialize node
cvchain init validator1 --chain-id cvchain-testnet-1

# Copy genesis.json from coordinator
# Start node
cvchain start
```

### Day 24-25: Genesis Ceremony

```bash
# On coordinator machine
cd ~/cvchain-testnet

# Create genesis
cvchain init coordinator --chain-id cvchain-testnet-1

# Add validator accounts
cvchain keys add validator1
cvchain keys add validator2
cvchain keys add validator3

# Add genesis accounts
cvchain add-genesis-account validator1 100000000ucvt
cvchain add-genesis-account validator2 100000000ucvt
cvchain add-genesis-account validator3 100000000ucvt

# Generate gentx for each validator
cvchain gentx validator1 10000000ucvt \
  --chain-id cvchain-testnet-1 \
  --moniker="Validator 1"

# Collect gentx
cvchain collect-gentxs

# Distribute genesis.json to all nodes
scp ~/.cvchain/config/genesis.json node1:/root/.cvchain/config/
scp ~/.cvchain/config/genesis.json node2:/root/.cvchain/config/
# etc.
```

### Day 26-27: Monitoring & Explorer

```bash
# Deploy Prometheus + Grafana
docker-compose up -d

# Deploy block explorer (Big Dipper)
git clone https://github.com/forbole/big-dipper-2.0-cosmos
cd big-dipper-2.0-cosmos
# Configure for CVChain
npm install
npm run build
npm start
```

### Day 28: Public Launch & Documentation

1. **Announce testnet** on social media
2. **Publish documentation** at docs.cvchain.io
3. **Launch faucet** for testnet tokens
4. **Onboard community validators**

**Launch Checklist:**
- ✅ 5+ validators online
- ✅ Block explorer accessible
- ✅ Faucet operational
- ✅ RPC/API endpoints public
- ✅ Documentation complete
- ✅ Monitoring alerts configured

---

## 📊 MONITORING COMMANDS

```bash
# Check node status
cvchain status

# Check validator info
cvchain query staking validator $(cvchain keys show validator1 -a --bech val)

# Check latest block
cvchain query block

# Monitor logs
journalctl -u cvchain -f

# Check peers
cvchain query tendermint-validator-set
```

---

## 🔗 USEFUL LINKS

### Development
- **CVChain Repo:** https://github.com/cyberviser/cvchain
- **Cosmos SDK Docs:** https://docs.cosmos.network/
- **Ignite CLI:** https://docs.ignite.com/

### Testnet
- **Explorer:** https://explorer.cvchain.io
- **Faucet:** https://faucet.cvchain.io
- **RPC:** https://rpc.cvchain.io
- **API:** https://api.cvchain.io

### Community
- **Discord:** https://discord.gg/cyberviser
- **Twitter:** https://twitter.com/cyberviser
- **Docs:** https://docs.cvchain.io

---

## ✅ FINAL CHECKLIST

### Week 1
- [ ] Go environment installed
- [ ] Ignite CLI installed
- [ ] Basic CVChain running
- [ ] Understand Cosmos SDK architecture

### Week 2
- [ ] x/audit module complete
- [ ] IPFS integration working
- [ ] CLI commands functional
- [ ] Unit tests passing

### Week 3
- [ ] x/security module operational
- [ ] x/reputation module operational
- [ ] All modules integrated
- [ ] Integration tests passing

### Week 4
- [ ] Testnet infrastructure deployed
- [ ] Genesis ceremony complete
- [ ] 5+ validators online
- [ ] Block explorer live
- [ ] Public launch announced

---

**You're ready to build CVChain! Start with Week 1, Day 1. Let's go! 🚀**
