#!/usr/bin/env bash
# Tails USB Creator for Hancock Security Operations
# Based on official Tails installation guide from https://tails.net/
# Creates bootable Tails USB for maximum-security operations

set -euo pipefail

TAILS_VERSION="7.7"
TAILS_IMG="tails-amd64-${TAILS_VERSION}.img"
TAILS_SIG="${TAILS_IMG}.sig"
TAILS_DOWNLOAD_URL="https://download.tails.net/tails/stable/${TAILS_IMG}"
TAILS_SIG_URL="https://tails.net/torrents/files/${TAILS_SIG}"
TAILS_SIGNING_KEY_URL="https://tails.net/tails-signing.key"
TAILS_SIGNING_KEY_FP="A490D0F4D311A4153E2BB7CADBB802B258ACD84F"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   Tails USB Creator for Hancock Security Operations${NC}"
    echo -e "${BLUE}   Maximum-Security Air-Gapped Operations Platform${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_prerequisites() {
    echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"
    
    # Check for required tools
    local missing_tools=()
    
    for tool in wget gpg dd lsblk; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "${RED}✗ Missing required tools: ${missing_tools[*]}${NC}"
        echo -e "${YELLOW}Install with: sudo apt install wget gnupg coreutils util-linux${NC}"
        exit 1
    fi
    
    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
        echo -e "${YELLOW}⚠ This script needs sudo access to write to USB devices${NC}"
        echo -e "${YELLOW}  You will be prompted for your password${NC}"
    fi
    
    echo -e "${GREEN}✓ All prerequisites met${NC}"
    echo ""
}

verify_tails_signing_key() {
    echo -e "${YELLOW}[2/7] Verifying Tails signing key...${NC}"
    
    # Download Tails signing key
    if [ ! -f "tails-signing.key" ]; then
        echo -e "${BLUE}  Downloading Tails signing key...${NC}"
        wget -q --show-progress "$TAILS_SIGNING_KEY_URL" || {
            echo -e "${RED}✗ Failed to download Tails signing key${NC}"
            exit 1
        }
    fi
    
    # Import key
    gpg --import < tails-signing.key 2>&1 | grep -q "imported" || {
        echo -e "${BLUE}  Key already imported${NC}"
    }
    
    # Check if Debian keyring is available for additional verification
    if dpkg -l debian-keyring &>/dev/null; then
        echo -e "${BLUE}  Debian keyring available for Web of Trust verification${NC}"
        # Import Chris Lamb's key from Debian keyring
        if [ -f /usr/share/keyrings/debian-keyring.gpg ]; then
            gpg --keyring=/usr/share/keyrings/debian-keyring.gpg --export chris@chris-lamb.co.uk | gpg --import 2>/dev/null || true
        fi
    else
        echo -e "${YELLOW}  ⚠ Debian keyring not installed - skipping Web of Trust check${NC}"
        echo -e "${YELLOW}    Install with: sudo apt install debian-keyring${NC}"
    fi
    
    # Verify key fingerprint
    local key_fp=$(gpg --fingerprint "$TAILS_SIGNING_KEY_FP" 2>/dev/null | grep -oP '[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}\s+[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}\s[0-9A-F]{4}' | tr -d ' ')
    
    if [ "$key_fp" == "${TAILS_SIGNING_KEY_FP}" ]; then
        echo -e "${GREEN}✓ Tails signing key verified${NC}"
    else
        echo -e "${RED}✗ Tails signing key fingerprint mismatch!${NC}"
        echo -e "${RED}  Expected: ${TAILS_SIGNING_KEY_FP}${NC}"
        echo -e "${RED}  Got: ${key_fp}${NC}"
        exit 1
    fi
    
    echo ""
}

download_tails() {
    echo -e "${YELLOW}[3/7] Downloading Tails ${TAILS_VERSION}...${NC}"
    echo -e "${BLUE}  Size: ~1.9 GB - this may take 10-20 minutes${NC}"
    
    if [ -f "$TAILS_IMG" ]; then
        echo -e "${BLUE}  ✓ Tails image already downloaded${NC}"
    else
        wget --continue --show-progress "$TAILS_DOWNLOAD_URL" || {
            echo -e "${RED}✗ Failed to download Tails image${NC}"
            exit 1
        }
        echo -e "${GREEN}✓ Downloaded Tails image${NC}"
    fi
    
    # Download signature
    if [ -f "$TAILS_SIG" ]; then
        echo -e "${BLUE}  ✓ Signature already downloaded${NC}"
    else
        wget -q "$TAILS_SIG_URL" || {
            echo -e "${RED}✗ Failed to download signature${NC}"
            exit 1
        }
        echo -e "${GREEN}✓ Downloaded signature${NC}"
    fi
    
    echo ""
}

verify_tails_signature() {
    echo -e "${YELLOW}[4/7] Verifying Tails image signature...${NC}"
    
    # Verify GPG signature
    if TZ=UTC gpg --no-options --keyid-format long --verify "$TAILS_SIG" "$TAILS_IMG" 2>&1 | grep -q "Good signature"; then
        echo -e "${GREEN}✓ Tails image signature valid${NC}"
        echo -e "${GREEN}✓ Image authenticity confirmed${NC}"
    else
        echo -e "${RED}✗ Signature verification failed!${NC}"
        echo -e "${RED}  The downloaded image may be compromised${NC}"
        exit 1
    fi
    
    echo ""
}

select_usb_device() {
    echo -e "${YELLOW}[5/7] Selecting USB device...${NC}"
    echo -e "${RED}⚠ WARNING: All data on the selected USB will be DESTROYED${NC}"
    echo ""
    
    # List available block devices
    echo -e "${BLUE}Available storage devices:${NC}"
    lsblk -d -o NAME,SIZE,TYPE,MOUNTPOINT | grep -v "loop"
    echo ""
    
    # Prompt for device
    read -p "Enter USB device name (e.g., sdb): " device_name
    
    if [ -z "$device_name" ]; then
        echo -e "${RED}✗ No device specified${NC}"
        exit 1
    fi
    
    USB_DEVICE="/dev/$device_name"
    
    if [ ! -b "$USB_DEVICE" ]; then
        echo -e "${RED}✗ Device $USB_DEVICE does not exist${NC}"
        exit 1
    fi
    
    # Confirm device selection
    local device_size=$(lsblk -d -n -o SIZE "$USB_DEVICE")
    echo -e "${YELLOW}Selected device: $USB_DEVICE ($device_size)${NC}"
    echo -e "${RED}⚠ ALL DATA ON THIS DEVICE WILL BE LOST${NC}"
    read -p "Are you absolutely sure? Type 'YES' to continue: " confirm
    
    if [ "$confirm" != "YES" ]; then
        echo -e "${YELLOW}Aborted by user${NC}"
        exit 0
    fi
    
    echo ""
}

write_tails_to_usb() {
    echo -e "${YELLOW}[6/7] Writing Tails to USB device...${NC}"
    echo -e "${BLUE}  This will take 3-10 minutes depending on USB speed${NC}"
    
    # Unmount device if mounted
    sudo umount "${USB_DEVICE}"* 2>/dev/null || true
    
    # Write image to USB
    sudo dd if="$TAILS_IMG" of="$USB_DEVICE" bs=16M oflag=direct status=progress || {
        echo -e "${RED}✗ Failed to write Tails to USB${NC}"
        exit 1
    }
    
    # Sync to ensure all data written
    sudo sync
    
    echo -e "${GREEN}✓ Tails successfully written to $USB_DEVICE${NC}"
    echo ""
}

print_success_instructions() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   Tails USB Created Successfully${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    echo -e "  1. ${YELLOW}Boot from USB${NC}"
    echo -e "     - Shut down your computer"
    echo -e "     - Insert the Tails USB stick"
    echo -e "     - Power on and press Boot Menu key (F12, F9, Esc, etc.)"
    echo -e "     - Select the USB device"
    echo ""
    echo -e "  2. ${YELLOW}First Boot${NC}"
    echo -e "     - Welcome Screen will appear in 1-2 minutes"
    echo -e "     - Select language and keyboard layout"
    echo -e "     - Click 'Start Tails'"
    echo ""
    echo -e "  3. ${YELLOW}Configure Persistent Storage (Optional)${NC}"
    echo -e "     - Applications → Tails → Configure Persistent Storage"
    echo -e "     - Create encrypted storage for:"
    echo -e "       • Browser bookmarks"
    echo -e "       • Network configurations"
    echo -e "       • Additional software"
    echo -e "       • Documents"
    echo ""
    echo -e "  4. ${YELLOW}Connect to Internet${NC}"
    echo -e "     - System menu → Wi-Fi"
    echo -e "     - Select network and connect"
    echo -e "     - Tor Connection assistant will guide you"
    echo ""
    echo -e "${BLUE}Hancock Integration:${NC}"
    echo -e "  - Use Tails for maximum-security operations"
    echo -e "  - All traffic automatically routed through Tor"
    echo -e "  - No traces left on host computer"
    echo -e "  - Perfect for high-sensitivity OSINT and reporting"
    echo ""
    echo -e "${BLUE}Boot Menu Keys by Manufacturer:${NC}"
    echo -e "  Acer:     F12, F9  | Dell:     F12"
    echo -e "  HP:       F9       | Lenovo:   F12, Novo"
    echo -e "  Asus:     Esc      | Samsung:  F12, F2"
    echo -e "  Apple:    Option   | Others:   F12, Esc"
    echo ""
    echo -e "${GREEN}For detailed documentation: https://tails.net/doc/index.en.html${NC}"
    echo ""
}

cleanup() {
    echo -e "${YELLOW}[7/7] Cleaning up...${NC}"
    
    # Optionally remove downloaded files
    read -p "Remove downloaded Tails image and signature? (y/n): " cleanup_choice
    
    if [ "$cleanup_choice" == "y" ]; then
        rm -f "$TAILS_IMG" "$TAILS_SIG" "tails-signing.key"
        echo -e "${GREEN}✓ Cleaned up downloaded files${NC}"
    else
        echo -e "${BLUE}  Keeping files for future USB creation${NC}"
    fi
    
    echo ""
}

main() {
    print_banner
    check_prerequisites
    verify_tails_signing_key
    download_tails
    verify_tails_signature
    select_usb_device
    write_tails_to_usb
    print_success_instructions
    cleanup
}

main "$@"
