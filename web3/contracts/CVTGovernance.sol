// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title CVT Governance Contract
 * @dev DAO governance for CyberViser ecosystem
 * @notice 1 CVT = 1 vote, proposals require quorum and majority
 * @author HancockForge / 0AI / CyberViser
 */
contract CVTGovernance is Ownable, ReentrancyGuard {
    IERC20 public cvtToken;
    
    uint256 public constant PROPOSAL_THRESHOLD = 10_000 * 10**18; // 10K CVT to create proposal
    uint256 public constant QUORUM_PERCENTAGE = 10; // 10% of total supply must vote
    uint256 public constant VOTING_PERIOD = 7 days;
    uint256 public constant EXECUTION_DELAY = 2 days; // Timelock
    
    uint256 public proposalCount;
    
    enum ProposalState {
        Pending,
        Active,
        Defeated,
        Succeeded,
        Queued,
        Executed,
        Cancelled
    }
    
    enum ProposalType {
        FeatureRequest,
        BudgetAllocation,
        Partnership,
        TreasuryManagement,
        ProtocolUpgrade,
        Other
    }
    
    struct Proposal {
        uint256 id;
        address proposer;
        string title;
        string description;
        ProposalType proposalType;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 startTime;
        uint256 endTime;
        uint256 executionTime;
        ProposalState state;
        mapping(address => bool) hasVoted;
        mapping(address => uint256) votes;
    }
    
    mapping(uint256 => Proposal) public proposals;
    
    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        string title,
        ProposalType proposalType,
        uint256 startTime,
        uint256 endTime
    );
    event Voted(
        uint256 indexed proposalId,
        address indexed voter,
        bool support,
        uint256 weight
    );
    event ProposalExecuted(uint256 indexed proposalId);
    event ProposalCancelled(uint256 indexed proposalId);
    event ProposalQueued(uint256 indexed proposalId, uint256 executionTime);
    
    /**
     * @dev Constructor
     * @param _cvtToken CVT token address
     */
    constructor(address _cvtToken) Ownable(msg.sender) {
        require(_cvtToken != address(0), "CVTGovernance: Zero address");
        cvtToken = IERC20(_cvtToken);
    }
    
    /**
     * @dev Create a governance proposal
     * @param title Proposal title
     * @param description Detailed description
     * @param proposalType Type of proposal
     */
    function createProposal(
        string memory title,
        string memory description,
        ProposalType proposalType
    ) external returns (uint256) {
        require(
            cvtToken.balanceOf(msg.sender) >= PROPOSAL_THRESHOLD,
            "CVTGovernance: Insufficient CVT to propose"
        );
        
        proposalCount++;
        uint256 proposalId = proposalCount;
        
        Proposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.proposalType = proposalType;
        proposal.startTime = block.timestamp;
        proposal.endTime = block.timestamp + VOTING_PERIOD;
        proposal.state = ProposalState.Active;
        
        emit ProposalCreated(
            proposalId,
            msg.sender,
            title,
            proposalType,
            proposal.startTime,
            proposal.endTime
        );
        
        return proposalId;
    }
    
    /**
     * @dev Vote on a proposal
     * @param proposalId Proposal ID
     * @param support true = for, false = against
     */
    function vote(uint256 proposalId, bool support) external nonReentrant {
        Proposal storage proposal = proposals[proposalId];
        
        require(proposal.state == ProposalState.Active, "CVTGovernance: Proposal not active");
        require(block.timestamp < proposal.endTime, "CVTGovernance: Voting ended");
        require(!proposal.hasVoted[msg.sender], "CVTGovernance: Already voted");
        
        uint256 votingPower = cvtToken.balanceOf(msg.sender);
        require(votingPower > 0, "CVTGovernance: No voting power");
        
        proposal.hasVoted[msg.sender] = true;
        proposal.votes[msg.sender] = votingPower;
        
        if (support) {
            proposal.votesFor += votingPower;
        } else {
            proposal.votesAgainst += votingPower;
        }
        
        emit Voted(proposalId, msg.sender, support, votingPower);
    }
    
    /**
     * @dev Finalize proposal after voting period
     * @param proposalId Proposal ID
     */
    function finalizeProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        
        require(proposal.state == ProposalState.Active, "CVTGovernance: Not active");
        require(block.timestamp >= proposal.endTime, "CVTGovernance: Voting not ended");
        
        uint256 totalVotes = proposal.votesFor + proposal.votesAgainst;
        uint256 totalSupply = cvtToken.totalSupply();
        uint256 quorum = (totalSupply * QUORUM_PERCENTAGE) / 100;
        
        // Check quorum
        if (totalVotes < quorum) {
            proposal.state = ProposalState.Defeated;
            return;
        }
        
        // Check majority
        if (proposal.votesFor > proposal.votesAgainst) {
            proposal.state = ProposalState.Succeeded;
            proposal.executionTime = block.timestamp + EXECUTION_DELAY;
            emit ProposalQueued(proposalId, proposal.executionTime);
        } else {
            proposal.state = ProposalState.Defeated;
        }
    }
    
    /**
     * @dev Execute a successful proposal (after timelock)
     * @param proposalId Proposal ID
     */
    function executeProposal(uint256 proposalId) external onlyOwner {
        Proposal storage proposal = proposals[proposalId];
        
        require(proposal.state == ProposalState.Succeeded, "CVTGovernance: Not succeeded");
        require(
            block.timestamp >= proposal.executionTime,
            "CVTGovernance: Timelock not expired"
        );
        
        proposal.state = ProposalState.Executed;
        
        emit ProposalExecuted(proposalId);
        
        // Actual execution logic would go here
        // For now, this is a signaling mechanism
    }
    
    /**
     * @dev Cancel a proposal (proposer or owner only)
     * @param proposalId Proposal ID
     */
    function cancelProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        
        require(
            msg.sender == proposal.proposer || msg.sender == owner(),
            "CVTGovernance: Not authorized"
        );
        require(
            proposal.state == ProposalState.Active || proposal.state == ProposalState.Succeeded,
            "CVTGovernance: Cannot cancel"
        );
        
        proposal.state = ProposalState.Cancelled;
        
        emit ProposalCancelled(proposalId);
    }
    
    /**
     * @dev Get proposal details
     * @param proposalId Proposal ID
     */
    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        string memory description,
        ProposalType proposalType,
        uint256 votesFor,
        uint256 votesAgainst,
        uint256 startTime,
        uint256 endTime,
        ProposalState state
    ) {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.title,
            proposal.description,
            proposal.proposalType,
            proposal.votesFor,
            proposal.votesAgainst,
            proposal.startTime,
            proposal.endTime,
            proposal.state
        );
    }
    
    /**
     * @dev Get proposal state
     * @param proposalId Proposal ID
     */
    function getProposalState(uint256 proposalId) external view returns (ProposalState) {
        return proposals[proposalId].state;
    }
    
    /**
     * @dev Check if user has voted
     * @param proposalId Proposal ID
     * @param user User address
     */
    function hasVoted(uint256 proposalId, address user) external view returns (bool) {
        return proposals[proposalId].hasVoted[user];
    }
    
    /**
     * @dev Get user's voting power
     * @param user User address
     */
    function getVotingPower(address user) external view returns (uint256) {
        return cvtToken.balanceOf(user);
    }
    
    /**
     * @dev Get current quorum requirement
     */
    function getQuorumVotes() external view returns (uint256) {
        return (cvtToken.totalSupply() * QUORUM_PERCENTAGE) / 100;
    }
}
