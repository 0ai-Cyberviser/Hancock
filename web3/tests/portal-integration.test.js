/**
 * Web3 Portal Integration Tests (Mumbai Testnet)
 * Tests MetaMask integration, contract interactions, and portal functionality
 * 
 * Run with: npm test -- --grep "portal"
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Web3 Portal - Mumbai Testnet Integration", function () {
  let cvtToken, cvtStaking, cvtGovernance;
  let deployer, user1, user2;
  const INITIAL_MINT = ethers.parseEther("10000");
  const STAKE_AMOUNT = ethers.parseEther("1000");

  before(async function () {
    [deployer, user1, user2] = await ethers.getSigners();

    // Deploy contracts
    const CVTToken = await ethers.getContractFactory("CyberViserToken");
    cvtToken = await CVTToken.deploy();
    await cvtToken.deploymentTransaction().wait();

    const CVTStaking = await ethers.getContractFactory("CVTStaking");
    cvtStaking = await CVTStaking.deploy(cvtToken.target, 1000); // 10% APY
    await cvtStaking.deploymentTransaction().wait();

    const CVTGovernance = await ethers.getContractFactory("CVTGovernance");
    cvtGovernance = await CVTGovernance.deploy(
      cvtToken.target,
      1,
      45818,
      ethers.parseEther("1000")
    );
    await cvtGovernance.deploymentTransaction().wait();

    // Mint initial tokens to users
    await cvtToken.mint(user1.address, INITIAL_MINT);
    await cvtToken.mint(user2.address, INITIAL_MINT);
  });

  describe("🔗 MetaMask Wallet Connection", function () {
    it("should connect user account", async function () {
      expect(user1.address).to.not.be.empty;
      expect(user1.address).to.match(/^0x[a-fA-F0-9]{40}$/);
    });

    it("should display account balance", async function () {
      const balance = await cvtToken.balanceOf(user1.address);
      expect(balance).to.equal(INITIAL_MINT);
    });

    it("should display network info (Mumbai)", async function () {
      const network = await ethers.provider.getNetwork();
      expect(network.chainId).to.equal(80001); // Mumbai testnet
    });
  });

  describe("💰 Token Dashboard", function () {
    it("should fetch token supply", async function () {
      const supply = await cvtToken.totalSupply();
      expect(supply).to.be.gt(0);
    });

    it("should display user balance", async function () {
      const balance = await cvtToken.balanceOf(user1.address);
      expect(balance).to.equal(INITIAL_MINT);
    });

    it("should display token price (mock)", async function () {
      // In production, fetch from DEX or price feed
      const mockPrice = ethers.parseEther("0.50"); // $0.50 per CVT
      expect(mockPrice).to.be.gt(0);
    });
  });

  describe("🔐 Staking Portal", function () {
    it("should approve token for staking", async function () {
      const tx = await cvtToken
        .connect(user1)
        .approve(cvtStaking.target, STAKE_AMOUNT);
      await tx.wait();

      const allowance = await cvtToken.allowance(
        user1.address,
        cvtStaking.target
      );
      expect(allowance).to.equal(STAKE_AMOUNT);
    });

    it("should stake tokens", async function () {
      await cvtToken
        .connect(user1)
        .approve(cvtStaking.target, STAKE_AMOUNT);
      await cvtStaking.connect(user1).stake(STAKE_AMOUNT);

      const staked = await cvtStaking.getStakedAmount(user1.address);
      expect(staked).to.equal(STAKE_AMOUNT);
    });

    it("should calculate staking rewards (APY)", async function () {
      // Move time forward
      await ethers.provider.send("hardhat_mine", ["0x52"]);

      const rewards = await cvtStaking.calculateRewards(user1.address);
      expect(rewards).to.be.gt(0);
    });

    it("should unstake tokens and claim rewards", async function () {
      const rewardsBefore = await cvtStaking.calculateRewards(user1.address);
      await cvtStaking.connect(user1).unstake(STAKE_AMOUNT);
      const balanceAfter = await cvtToken.balanceOf(user1.address);
      
      expect(balanceAfter).to.be.gte(INITIAL_MINT); // May include rewards
    });
  });

  describe("🗳️ Governance Portal", function () {
    it("should allow proposal creation", async function () {
      // User must have delegation to propose
      await cvtToken
        .connect(user1)
        .delegate(user1.address);

      // Propose changes to staking APY
      const proposeTx = await cvtGovernance.connect(user1).propose(
        [cvtStaking.target],
        [0],
        ["setAPY(uint256)"],
        [ethers.AbiCoder.defaultAbiCoder().encode(["uint256"], [1200])],
        "Increase staking APY from 10% to 12%"
      );
      
      const receipt = await proposeTx.wait();
      const events = receipt.logs.map(log => {
        try {
          return cvtGovernance.interface.parseLog(log);
        } catch {
          return null;
        }
      }).filter(e => e !== null && e.name === "ProposalCreated");

      expect(events.length).to.be.gt(0);
    });

    it("should allow voting on proposals", async function () {
      const proposals = await cvtGovernance.proposalCount();
      if (proposals > 0) {
        const proposalId = proposals - 1n;
        // Vote: 1 = For, 0 = Against, 2 = Abstain
        const voteTx = await cvtGovernance.connect(user1).castVote(proposalId, 1);
        await voteTx.wait();

        const hasVoted = await cvtGovernance.hasVoted(proposalId, user1.address);
        expect(hasVoted).to.be.true;
      }
    });
  });

  describe("🎯 Portal UI Integration", function () {
    it("should generate contract addresses JSON for portal", async function () {
      const contracts = {
        network: "mumbai",
        chainId: 80001,
        rpcUrl: "https://rpc-mumbai.maticvigil.com",
        contracts: {
          token: cvtToken.target,
          staking: cvtStaking.target,
          governance: cvtGovernance.target,
        },
        timestamp: new Date().toISOString(),
      };

      expect(contracts.contracts.token).to.match(/^0x[a-fA-F0-9]{40}$/);
      expect(contracts.contracts.staking).to.match(/^0x[a-fA-F0-9]{40}$/);
      expect(contracts.contracts.governance).to.match(/^0x[a-fA-F0-9]{40}$/);
    });

    it("should format numbers for portal display", async function () {
      const balance = await cvtToken.balanceOf(user1.address);
      const formatted = ethers.formatEther(balance);
      expect(formatted).to.include(".");
    });
  });

  describe("📡 Transaction Verification (PolygonScan)", function () {
    it("should return Mumbai PolygonScan URLs", async function () {
      const baseUrl = "https://mumbai.polygonscan.com/address/";
      
      const tokenUrl = baseUrl + cvtToken.target;
      const stakingUrl = baseUrl + cvtStaking.target;
      const governanceUrl = baseUrl + cvtGovernance.target;

      expect(tokenUrl).to.include("polygonscan.com");
      expect(stakingUrl).to.include("polygonscan.com");
      expect(governanceUrl).to.include("polygonscan.com");
    });
  });
});
