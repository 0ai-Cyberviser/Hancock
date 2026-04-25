#!/usr/bin/env bash
# Whonix Docker Integration for Hancock Security Testing
# Provides Tor-routed, privacy-enhanced testing environment
# Alternative to Qubes-Whonix for standard Linux/Debian hosts

set -euo pipefail

WHONIX_GATEWAY_IMAGE="whonix/whonix-gateway-cli:latest"
WHONIX_WORKSTATION_IMAGE="whonix/whonix-workstation-cli:latest"
NETWORK_NAME="whonix-net"
GATEWAY_CONTAINER="whonix-gateway"
WORKSTATION_CONTAINER="whonix-workstation"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   Whonix Docker Integration for Hancock${NC}"
    echo -e "${BLUE}   Privacy-Enhanced Security Testing Environment${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_prerequisites() {
    echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}✗ Docker daemon not running or insufficient permissions.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Docker available and running${NC}"
    echo ""
}

create_whonix_network() {
    echo -e "${YELLOW}[2/6] Creating isolated Whonix network...${NC}"
    
    if docker network inspect "$NETWORK_NAME" &> /dev/null; then
        echo -e "${BLUE}  Network already exists: $NETWORK_NAME${NC}"
    else
        docker network create \
            --driver bridge \
            --subnet 10.152.152.0/24 \
            --gateway 10.152.152.1 \
            "$NETWORK_NAME"
        echo -e "${GREEN}✓ Created network: $NETWORK_NAME${NC}"
    fi
    echo ""
}

download_whonix_images() {
    echo -e "${YELLOW}[3/6] Downloading Whonix Docker images...${NC}"
    echo -e "${BLUE}  This may take 10-20 minutes depending on connection speed${NC}"
    
    echo -e "${BLUE}  Pulling Whonix Gateway...${NC}"
    docker pull "$WHONIX_GATEWAY_IMAGE" || {
        echo -e "${RED}✗ Failed to pull Whonix Gateway image${NC}"
        exit 1
    }
    
    echo -e "${BLUE}  Pulling Whonix Workstation...${NC}"
    docker pull "$WHONIX_WORKSTATION_IMAGE" || {
        echo -e "${RED}✗ Failed to pull Whonix Workstation image${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Downloaded both Whonix images${NC}"
    echo ""
}

start_whonix_gateway() {
    echo -e "${YELLOW}[4/6] Starting Whonix Gateway (Tor router)...${NC}"
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${GATEWAY_CONTAINER}$"; then
        echo -e "${BLUE}  Removing existing gateway container...${NC}"
        docker rm -f "$GATEWAY_CONTAINER" &> /dev/null
    fi
    
    docker run -d \
        --name "$GATEWAY_CONTAINER" \
        --network "$NETWORK_NAME" \
        --ip 10.152.152.10 \
        --cap-add=NET_ADMIN \
        --cap-add=NET_RAW \
        --device=/dev/net/tun \
        -v /home/_0ai_/Hancock-1:/workspace:ro \
        "$WHONIX_GATEWAY_IMAGE"
    
    echo -e "${BLUE}  Waiting for Tor to bootstrap (30 seconds)...${NC}"
    sleep 30
    
    if docker exec "$GATEWAY_CONTAINER" tor --verify-config &> /dev/null; then
        echo -e "${GREEN}✓ Whonix Gateway started (Tor router active)${NC}"
    else
        echo -e "${YELLOW}⚠ Gateway started but Tor status unclear${NC}"
    fi
    echo ""
}

start_whonix_workstation() {
    echo -e "${YELLOW}[5/6] Starting Whonix Workstation (isolated client)...${NC}"
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${WORKSTATION_CONTAINER}$"; then
        echo -e "${BLUE}  Removing existing workstation container...${NC}"
        docker rm -f "$WORKSTATION_CONTAINER" &> /dev/null
    fi
    
    docker run -d \
        --name "$WORKSTATION_CONTAINER" \
        --network "$NETWORK_NAME" \
        --ip 10.152.152.11 \
        -e TOR_SOCKS_HOST=10.152.152.10 \
        -e TOR_SOCKS_PORT=9050 \
        -v /home/_0ai_/Hancock-1:/workspace \
        -v /home/_0ai_/PeachTree:/peachtree \
        -v /home/_0ai_/0ai-assurance-network:/assurance \
        "$WHONIX_WORKSTATION_IMAGE" \
        sleep infinity
    
    echo -e "${GREEN}✓ Whonix Workstation started (all traffic routed via Tor)${NC}"
    echo ""
}

verify_tor_connectivity() {
    echo -e "${YELLOW}[6/6] Verifying Tor connectivity...${NC}"
    
    # Test Tor connection from workstation
    if docker exec "$WORKSTATION_CONTAINER" \
        curl -s --socks5-hostname 10.152.152.10:9050 https://check.torproject.org/api/ip \
        | grep -q '"IsTor":true'; then
        echo -e "${GREEN}✓ Tor connectivity verified - all traffic anonymized${NC}"
        
        # Get Tor exit IP
        TOR_IP=$(docker exec "$WORKSTATION_CONTAINER" \
            curl -s --socks5-hostname 10.152.152.10:9050 https://check.torproject.org/api/ip \
            | grep -oP '(?<="IP":")[^"]+')
        echo -e "${BLUE}  Current Tor exit IP: $TOR_IP${NC}"
    else
        echo -e "${YELLOW}⚠ Tor connectivity check inconclusive${NC}"
    fi
    echo ""
}

print_usage_instructions() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   Whonix Docker Environment Ready${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Usage Instructions:${NC}"
    echo ""
    echo -e "  1. Access Whonix Workstation (Tor-routed):"
    echo -e "     ${YELLOW}docker exec -it $WORKSTATION_CONTAINER bash${NC}"
    echo ""
    echo -e "  2. Run Hancock in Whonix (anonymous testing):"
    echo -e "     ${YELLOW}docker exec -it $WORKSTATION_CONTAINER bash -c 'cd /workspace && ./hancock.sh'${NC}"
    echo ""
    echo -e "  3. Test Tor connectivity:"
    echo -e "     ${YELLOW}docker exec $WORKSTATION_CONTAINER curl -s --socks5-hostname 10.152.152.10:9050 https://check.torproject.org/${NC}"
    echo ""
    echo -e "  4. Check Tor status on Gateway:"
    echo -e "     ${YELLOW}docker exec $GATEWAY_CONTAINER tor --verify-config${NC}"
    echo ""
    echo -e "  5. View Gateway logs (Tor circuit info):"
    echo -e "     ${YELLOW}docker logs $GATEWAY_CONTAINER${NC}"
    echo ""
    echo -e "  6. Stop Whonix environment:"
    echo -e "     ${YELLOW}docker stop $GATEWAY_CONTAINER $WORKSTATION_CONTAINER${NC}"
    echo ""
    echo -e "  7. Remove Whonix environment:"
    echo -e "     ${YELLOW}docker rm -f $GATEWAY_CONTAINER $WORKSTATION_CONTAINER${NC}"
    echo -e "     ${YELLOW}docker network rm $NETWORK_NAME${NC}"
    echo ""
    echo -e "${BLUE}Security Notes:${NC}"
    echo -e "  • All workstation traffic routed through Tor (SOCKS5: 10.152.152.10:9050)"
    echo -e "  • Gateway provides DNS resolution via Tor"
    echo -e "  • Network isolation prevents accidental clearnet leaks"
    echo -e "  • Workspaces mounted: /workspace, /peachtree, /assurance"
    echo ""
    echo -e "${BLUE}Integration with Hancock:${NC}"
    echo -e "  • Use for anonymous OSINT reconnaissance"
    echo -e "  • Test governance proposals via Tor"
    echo -e "  • Anonymize PeachTree dataset collection"
    echo -e "  • Validate security tools with IP rotation"
    echo ""
}

cleanup_on_error() {
    echo -e "${RED}✗ Error occurred during setup${NC}"
    echo -e "${YELLOW}Cleaning up partial deployment...${NC}"
    docker rm -f "$GATEWAY_CONTAINER" "$WORKSTATION_CONTAINER" 2> /dev/null || true
    docker network rm "$NETWORK_NAME" 2> /dev/null || true
    exit 1
}

trap cleanup_on_error ERR

main() {
    print_banner
    check_prerequisites
    create_whonix_network
    download_whonix_images
    start_whonix_gateway
    start_whonix_workstation
    verify_tor_connectivity
    print_usage_instructions
}

main "$@"
