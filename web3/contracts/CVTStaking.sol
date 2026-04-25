// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CVT Staking Contract
 * @dev Stake CVT tokens to earn rewards and governance voting power
 * @notice APY: 10% base rate, increases with early staker bonuses
 * @author HancockForge / 0AI / CyberViser
 */
contract CVTStaking is ReentrancyGuard, Ownable {
    IERC20 public cvtToken;
    
    uint256 public constant MIN_STAKE = 100 * 10**18; // 100 CVT minimum
    uint256 public constant REWARD_RATE = 10; // 10% APY base rate
    uint256 public constant YEAR = 365 days;
    uint256 public constant EARLY_STAKER_BONUS = 25; // 25% bonus for early stakers
    uint256 public constant EARLY_STAKER_CUTOFF = 30 days; // First 30 days
    
    uint256 public deploymentTimestamp;
    uint256 public totalStaked;
    uint256 public totalRewardsPaid;
    
    struct Stake {
        uint256 amount;
        uint256 timestamp;
        uint256 rewardDebt;
        uint256 lastClaimTime;
    }
    
    mapping(address => Stake) public stakes;
    address[] public stakers;
    
    event Staked(address indexed user, uint256 amount, uint256 totalStaked);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardsClaimed(address indexed user, uint256 reward);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    
    /**
     * @dev Constructor
     * @param _cvtToken CVT token address
     */
    constructor(address _cvtToken) Ownable(msg.sender) {
        require(_cvtToken != address(0), "CVTStaking: Zero address");
        cvtToken = IERC20(_cvtToken);
        deploymentTimestamp = block.timestamp;
    }
    
    /**
     * @dev Stake CVT tokens
     * @param amount Amount to stake (must be >= MIN_STAKE)
     */
    function stake(uint256 amount) external nonReentrant {
        require(amount >= MIN_STAKE, "CVTStaking: Below minimum stake");
        
        // Claim existing rewards before adding new stake
        if (stakes[msg.sender].amount > 0) {
            _claimRewards(msg.sender);
        } else {
            // New staker
            stakers.push(msg.sender);
        }
        
        // Transfer tokens from user
        require(
            cvtToken.transferFrom(msg.sender, address(this), amount),
            "CVTStaking: Transfer failed"
        );
        
        // Update stake
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].timestamp = block.timestamp;
        stakes[msg.sender].lastClaimTime = block.timestamp;
        totalStaked += amount;
        
        emit Staked(msg.sender, amount, stakes[msg.sender].amount);
    }
    
    /**
     * @dev Unstake CVT tokens (claims rewards automatically)
     * @param amount Amount to unstake
     */
    function unstake(uint256 amount) external nonReentrant {
        require(stakes[msg.sender].amount >= amount, "CVTStaking: Insufficient stake");
        
        // Claim all pending rewards
        uint256 reward = _claimRewards(msg.sender);
        
        // Update stake
        stakes[msg.sender].amount -= amount;
        totalStaked -= amount;
        
        // Transfer staked tokens back
        require(cvtToken.transfer(msg.sender, amount), "CVTStaking: Transfer failed");
        
        emit Unstaked(msg.sender, amount, reward);
    }
    
    /**
     * @dev Calculate pending rewards for a user
     * @param user User address
     * @return Pending reward amount
     */
    function calculateReward(address user) public view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;
        
        uint256 stakingDuration = block.timestamp - userStake.lastClaimTime;
        uint256 effectiveRate = REWARD_RATE;
        
        // Early staker bonus (first 30 days after contract deployment)
        if (block.timestamp < deploymentTimestamp + EARLY_STAKER_CUTOFF) {
            effectiveRate = REWARD_RATE + (REWARD_RATE * EARLY_STAKER_BONUS / 100);
        }
        
        // Calculate reward: (amount * rate * duration) / (100 * YEAR)
        uint256 reward = (userStake.amount * effectiveRate * stakingDuration) / (100 * YEAR);
        
        return reward;
    }
    
    /**
     * @dev Claim rewards without unstaking
     */
    function claimRewards() external nonReentrant {
        _claimRewards(msg.sender);
    }
    
    /**
     * @dev Internal function to claim rewards
     * @param user User address
     * @return Reward amount claimed
     */
    function _claimRewards(address user) internal returns (uint256) {
        uint256 reward = calculateReward(user);
        
        if (reward > 0) {
            stakes[user].rewardDebt += reward;
            stakes[user].lastClaimTime = block.timestamp;
            totalRewardsPaid += reward;
            
            require(cvtToken.transfer(user, reward), "CVTStaking: Reward transfer failed");
            emit RewardsClaimed(user, reward);
        }
        
        return reward;
    }
    
    /**
     * @dev Emergency withdraw (forfeit rewards)
     * Use only if something goes wrong
     */
    function emergencyWithdraw() external nonReentrant {
        uint256 amount = stakes[msg.sender].amount;
        require(amount > 0, "CVTStaking: No stake to withdraw");
        
        // Reset stake
        stakes[msg.sender].amount = 0;
        stakes[msg.sender].rewardDebt = 0;
        totalStaked -= amount;
        
        // Transfer without rewards
        require(cvtToken.transfer(msg.sender, amount), "CVTStaking: Transfer failed");
        
        emit EmergencyWithdraw(msg.sender, amount);
    }
    
    /**
     * @dev Get stake info for a user
     * @param user User address
     * @return amount Staked amount
     * @return pendingReward Pending rewards
     * @return stakingDuration Time staked (seconds)
     */
    function getStakeInfo(address user) external view returns (
        uint256 amount,
        uint256 pendingReward,
        uint256 stakingDuration
    ) {
        Stake memory userStake = stakes[user];
        amount = userStake.amount;
        pendingReward = calculateReward(user);
        stakingDuration = userStake.amount > 0 ? block.timestamp - userStake.timestamp : 0;
    }
    
    /**
     * @dev Get total number of stakers
     */
    function getTotalStakers() external view returns (uint256) {
        return stakers.length;
    }
    
    /**
     * @dev Get APY for current period
     * @return Current APY (with early staker bonus if applicable)
     */
    function getCurrentAPY() external view returns (uint256) {
        if (block.timestamp < deploymentTimestamp + EARLY_STAKER_CUTOFF) {
            return REWARD_RATE + (REWARD_RATE * EARLY_STAKER_BONUS / 100);
        }
        return REWARD_RATE;
    }
    
    /**
     * @dev Check if early staker bonus is still active
     */
    function isEarlyStakerPeriod() external view returns (bool) {
        return block.timestamp < deploymentTimestamp + EARLY_STAKER_CUTOFF;
    }
}
