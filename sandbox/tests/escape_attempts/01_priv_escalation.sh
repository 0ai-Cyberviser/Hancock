#!/bin/bash
# Privilege Escalation Attack Payloads
# These scripts attempt to escalate privileges inside the Hancock sandbox.
# ALL attempts should FAIL if sandbox is properly hardened.

set -e

echo "=========================================="
echo "PRIVILEGE ESCALATION ATTACK PAYLOADS"
echo "=========================================="
echo "Testing: Hancock Sandbox Isolation"
echo "Expected: ALL attacks should be BLOCKED"
echo "=========================================="

# Attack 1: sudo privilege escalation
echo -e "\n[1] Attempting sudo privilege escalation..."
if command -v sudo &> /dev/null; then
    echo "⚠️  sudo binary found (unexpected in hardened container)"
    sudo -l && echo "❌ FAIL: sudo succeeded" || echo "✅ PASS: sudo blocked"
else
    echo "✅ PASS: sudo not available"
fi

# Attack 2: setuid binary abuse
echo -e "\n[2] Searching for setuid binaries..."
SETUID_COUNT=$(find / -perm -4000 -type f 2>/dev/null | wc -l)
if [ "$SETUID_COUNT" -gt 0 ]; then
    echo "⚠️  Found $SETUID_COUNT setuid binaries:"
    find / -perm -4000 -type f 2>/dev/null | head -5
    echo "❌ POTENTIAL RISK: setuid binaries present"
else
    echo "✅ PASS: No setuid binaries found"
fi

# Attack 3: Capability escalation
echo -e "\n[3] Checking dangerous capabilities..."
CAPS=$(cat /proc/self/status | grep Cap)
echo "$CAPS"
if echo "$CAPS" | grep -qv "0000000000000000"; then
    echo "⚠️  Non-zero capabilities detected"
    echo "❌ POTENTIAL RISK: Container has capabilities"
else
    echo "✅ PASS: All capabilities dropped"
fi

# Attack 4: /etc/passwd modification
echo -e "\n[4] Attempting to modify /etc/passwd..."
echo "testuser:x:0:0::/:/bin/sh" >> /etc/passwd 2>&1 && \
    echo "❌ FAIL: /etc/passwd is writable!" || \
    echo "✅ PASS: /etc/passwd is read-only"

# Attack 5: /etc/shadow access
echo -e "\n[5] Attempting to read /etc/shadow..."
cat /etc/shadow 2>&1 > /dev/null && \
    echo "❌ FAIL: /etc/shadow is readable!" || \
    echo "✅ PASS: /etc/shadow access denied"

# Attack 6: su to root
echo -e "\n[6] Attempting su to root..."
echo "" | su - root 2>&1 | head -3
if [ $? -eq 0 ]; then
    echo "❌ FAIL: su succeeded!"
else
    echo "✅ PASS: su blocked"
fi

# Attack 7: pkexec abuse (if present)
echo -e "\n[7] Checking for pkexec..."
if command -v pkexec &> /dev/null; then
    echo "⚠️  pkexec found (CVE-2021-4034 PwnKit risk)"
    pkexec --version
    echo "❌ POTENTIAL RISK: pkexec present"
else
    echo "✅ PASS: pkexec not available"
fi

# Attack 8: dbus privilege escalation
echo -e "\n[8] Checking for D-Bus (local privilege escalation vector)..."
if command -v dbus-daemon &> /dev/null; then
    echo "⚠️  D-Bus found"
    echo "❌ POTENTIAL RISK: D-Bus present"
else
    echo "✅ PASS: D-Bus not available"
fi

echo -e "\n=========================================="
echo "PRIVILEGE ESCALATION TEST COMPLETE"
echo "=========================================="
