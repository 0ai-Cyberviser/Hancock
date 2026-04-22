#!/bin/bash
# File System Escape Attack Payloads
# These scripts attempt to escape via filesystem exploits.
# ALL attempts should be BLOCKED by read-only root + tmpfs.

set +e

echo "=========================================="
echo "FILE SYSTEM ESCAPE ATTACK PAYLOADS"
echo "=========================================="
echo "Testing: Filesystem Isolation & Read-Only Root"
echo "Expected: ALL write attempts BLOCKED (except /tmp)"
echo "=========================================="

# Attack 1: Root filesystem modification
echo -e "\n[1] Attempting to write to root filesystem..."
echo "evil" > /etc/evil.txt 2>&1
if [ -f /etc/evil.txt ]; then
    echo "❌ CRITICAL: Root filesystem is writable!"
    rm -f /etc/evil.txt
else
    echo "✅ PASS: Root filesystem is read-only"
fi

# Attack 2: /etc/passwd modification
echo -e "\n[2] Attempting to modify /etc/passwd..."
echo "hacker:x:0:0::/:/bin/sh" >> /etc/passwd 2>&1
if tail -1 /etc/passwd | grep -q "hacker"; then
    echo "❌ CRITICAL: /etc/passwd modified!"
else
    echo "✅ PASS: /etc/passwd modification blocked"
fi

# Attack 3: Path traversal to host filesystem
echo -e "\n[3] Attempting path traversal..."
cat ../../../../etc/hostname 2>&1 | head -3
cat ../../../../proc/version 2>&1 | head -3
if cat ../../../../etc/hostname 2>&1 | grep -qv "No such file"; then
    echo "⚠️  Path traversal succeeded"
else
    echo "✅ PASS: Path traversal blocked or limited to container"
fi

# Attack 4: Symlink attack to escape
echo -e "\n[4] Attempting symlink to host filesystem..."
ln -s /host/etc/shadow /tmp/shadow 2>&1
if [ -L /tmp/shadow ]; then
    echo "Symlink created, attempting to read..."
    cat /tmp/shadow 2>&1
    if [ $? -eq 0 ]; then
        echo "❌ CRITICAL: Symlink escape succeeded!"
    else
        echo "✅ PASS: Symlink target inaccessible"
    fi
    rm -f /tmp/shadow
else
    echo "✅ PASS: Symlink creation failed (no /host mount)"
fi

# Attack 5: Mount new filesystem
echo -e "\n[5] Attempting to mount new filesystem..."
mkdir -p /mnt/test 2>/dev/null
mount -t tmpfs tmpfs /mnt/test 2>&1
if mountpoint -q /mnt/test 2>/dev/null; then
    echo "❌ CRITICAL: Mount succeeded!"
    umount /mnt/test
else
    echo "✅ PASS: Mount operation blocked"
fi

# Attack 6: Bind mount attack
echo -e "\n[6] Attempting bind mount..."
mount --bind /etc /tmp/etc 2>&1
if [ -d /tmp/etc ]; then
    echo "❌ CRITICAL: Bind mount succeeded!"
    umount /tmp/etc
    rmdir /tmp/etc
else
    echo "✅ PASS: Bind mount blocked"
fi

# Attack 7: /proc/self/root escape
echo -e "\n[7] Attempting /proc/self/root escape..."
ls -la /proc/self/root/etc/hostname 2>&1 | head -3
if cat /proc/self/root/etc/hostname 2>&1 | grep -qv container; then
    echo "⚠️  /proc/self/root may leak host info"
else
    echo "✅ PASS: /proc/self/root shows container filesystem"
fi

# Attack 8: Hard link attack
echo -e "\n[8] Attempting hard link to sensitive file..."
ln /etc/shadow /tmp/shadow_link 2>&1
if [ -f /tmp/shadow_link ]; then
    echo "⚠️  Hard link created"
    cat /tmp/shadow_link 2>&1
    rm -f /tmp/shadow_link
else
    echo "✅ PASS: Hard link creation blocked"
fi

# Attack 9: /tmp tmpfs size limit bypass
echo -e "\n[9] Testing /tmp tmpfs size limit..."
dd if=/dev/zero of=/tmp/huge bs=1M count=100 2>&1 | tail -3
if [ -f /tmp/huge ]; then
    SIZE=$(du -sh /tmp/huge 2>/dev/null | cut -f1)
    echo "Created file: $SIZE"
    rm -f /tmp/huge
    echo "✅ PASS: /tmp write succeeded but limited to tmpfs size"
else
    echo "✅ PASS: /tmp write blocked at size limit"
fi

# Attack 10: Executable in /tmp (noexec check)
echo -e "\n[10] Testing /tmp noexec mount option..."
echo '#!/bin/bash\necho "EXECUTED"' > /tmp/test.sh
chmod +x /tmp/test.sh
/tmp/test.sh 2>&1
if [ $? -eq 0 ]; then
    echo "⚠️  /tmp is executable (noexec not enforced)"
else
    echo "✅ PASS: /tmp noexec enforced"
fi
rm -f /tmp/test.sh

# Attack 11: Check for Docker layer mounts
echo -e "\n[11] Checking for Docker layer mounts..."
cat /proc/mounts | grep -E "(overlay|aufs|btrfs)"
echo "✅ INFO: Docker layers visible (expected)"

# Attack 12: /dev/shm exploitation
echo -e "\n[12] Testing /dev/shm..."
if [ -d /dev/shm ]; then
    echo "test" > /dev/shm/test 2>&1
    if [ -f /dev/shm/test ]; then
        echo "⚠️  /dev/shm is writable"
        rm -f /dev/shm/test
    else
        echo "✅ PASS: /dev/shm write blocked"
    fi
else
    echo "✅ PASS: /dev/shm not available"
fi

echo -e "\n=========================================="
echo "FILE SYSTEM ESCAPE TEST COMPLETE"
echo "=========================================="
echo ""
echo "SUMMARY:"
echo "- Root filesystem should be READ-ONLY"
echo "- /tmp should be writable but size-limited"
echo "- /tmp should have noexec flag"
echo "- No host filesystem mounts should be accessible"
echo "- Path traversal should be contained within container"
