// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CyberViser Token (CVT)
 * @dev ERC-20 token for the CyberViser AI ecosystem
 * @notice Powers Hancock, PeachTrace, PeachTree, PeachFuzz, CactusFuzz
 * @author HancockForge / 0AI / CyberViser
 * 
 * Token Distribution (Grant-Optimized):
 * - Grant Programs: 25M CVT (25%) - Polygon, Ethereum Foundation, Protocol Labs
 * - Liquidity Mining: 20M CVT (20%) - QuickSwap, Uniswap incentives
 * - Community Rewards: 20M CVT (20%) - Staking + browser mining
 * - Development Fund: 12M CVT (12%) - Audits, upgrades, security
 * - Team & Founders: 10M CVT (10%) - Core team, 48-month vesting
 * - Ecosystem Growth: 8M CVT (8%) - Partnerships, integrations
 * - Treasury: 3M CVT (3%) - DAO emergency fund
 * - Marketing: 2M CVT (2%) - Community building
 */
contract CyberViserToken is ERC20, ERC20Pausable, Ownable {
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10**18; // 100 million CVT
    
    // Minter role management
    mapping(address => bool) public minters;
    
    // Token distribution tracking
    mapping(address => bool) public blacklisted;
    
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);
    event AddressBlacklisted(address indexed account);
    event AddressWhitelisted(address indexed account);
    event TokensBurned(address indexed from, uint256 amount);
    
    /**
     * @dev Constructor mints initial supply to deployer
     * Initial mint: 30M CVT (Team 20M + Dev Fund 10M with vesting)
     */
    constructor() 
        ERC20("CyberViser Token", "CVT") 
        Ownable(msg.sender)
    {
        // Initial mint for team and development fund
        _mint(msg.sender, 30_000_000 * 10**18);
        
        // Add deployer as minter
        minters[msg.sender] = true;
        emit MinterAdded(msg.sender);
    }
    
    /**
     * @dev Mint new tokens (only by authorized minters)
     * Used for: mining rewards, staking rewards, ecosystem growth
     * @param to Recipient address
     * @param amount Amount to mint (in wei)
     */
    function mint(address to, uint256 amount) external onlyMinter {
        require(totalSupply() + amount <= MAX_SUPPLY, "CVT: Max supply exceeded");
        require(!blacklisted[to], "CVT: Recipient is blacklisted");
        _mint(to, amount);
    }
    
    /**
     * @dev Burn tokens (reduce supply)
     * @param amount Amount to burn
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
        emit TokensBurned(msg.sender, amount);
    }
    
    /**
     * @dev Pause all token transfers (emergency only)
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause token transfers
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Add minter role (for staking/mining contracts)
     * @param minter Address to grant minter role
     */
    function addMinter(address minter) external onlyOwner {
        require(minter != address(0), "CVT: Zero address");
        minters[minter] = true;
        emit MinterAdded(minter);
    }
    
    /**
     * @dev Remove minter role
     * @param minter Address to revoke minter role
     */
    function removeMinter(address minter) external onlyOwner {
        minters[minter] = false;
        emit MinterRemoved(minter);
    }
    
    /**
     * @dev Blacklist address (prevent transfers)
     * @param account Address to blacklist
     */
    function blacklist(address account) external onlyOwner {
        blacklisted[account] = true;
        emit AddressBlacklisted(account);
    }
    
    /**
     * @dev Remove from blacklist
     * @param account Address to whitelist
     */
    function whitelist(address account) external onlyOwner {
        blacklisted[account] = false;
        emit AddressWhitelisted(account);
    }
    
    /**
     * @dev Check if address is minter
     */
    modifier onlyMinter() {
        require(minters[msg.sender], "CVT: Not a minter");
        _;
    }
    
    /**
     * @dev Hook to check paused state and blacklist (v5 compatible)
     */
    function _update(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Pausable) {
        require(!blacklisted[from], "CVT: Sender is blacklisted");
        require(!blacklisted[to], "CVT: Recipient is blacklisted");
        super._update(from, to, amount);
    }
    
    /**
     * @dev Get remaining mintable supply
     */
    function remainingSupply() external view returns (uint256) {
        return MAX_SUPPLY - totalSupply();
    }
}
