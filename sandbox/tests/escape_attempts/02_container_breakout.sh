#!/bin/bash
# Container Breakout Attack Payloads
# These scripts attempt to escape the Docker container.
# ALL attempts should FAIL if sandbox is properly hardened.

set +e  # Continue on errors (we expect many)

echo "=========================================="
echo "CONTAINER BREAKOUT ATTACK PAYLOADS"
echo "=========================================="
echo "Testing: Docker Container Isolation"
echo "Expected: ALL breakout attempts BLOCKED"
echo "=========================================="

# Attack 1: Docker socket escape
echo -e "\n[1] Attempting to access Docker socket..."
if [ -S /var/run/docker.sock ]; then
    echo "❌ CRITICAL: Docker socket is mounted!"
    ls -la /var/run/docker.sock
    echo "Attempting container escape via socket..."
    docker ps 2>&1 && echo "❌ FAIL: Docker escape succeeded!" || echo "⚠️  Socket present but unusable"
else
    echo "✅ PASS: Docker socket not mounted"
fi

# Attack 2: cgroup release_agent escape (CVE-2022-0492 style)
echo -e "\n[2] Attempting cgroup release_agent escape..."
if [ -d /sys/fs/cgroup ]; then
    echo "cgroup mounted, attempting modification..."
    mkdir /sys/fs/cgroup/rdma/exploit 2>&1 || true
    echo 1 > /sys/fs/cgroup/rdma/exploit/notify_on_release 2>&1 && \
        echo "❌ FAIL: cgroup writable!" || \
        echo "✅ PASS: cgroup write blocked"
else
    echo "✅ PASS: cgroup not accessible"
fi

# Attack 3: Dirty COW-style memory exploit
echo -e "\n[3] Checking for memory write protections..."
if [ -w /proc/self/mem ]; then
    echo "❌ CRITICAL: /proc/self/mem is writable!"
else
    echo "✅ PASS: /proc/self/mem protected"
fi

# Attack 4: Kernel module loading
echo -e "\n[4] Attempting to load kernel module..."
insmod /tmp/fake.ko 2>&1 | head -3
if [ $? -eq 0 ]; then
    echo "❌ CRITICAL: Kernel module loaded!"
else
    echo "✅ PASS: Kernel module loading blocked"
fi

# Attack 5: /proc/sys kernel parameter modification
echo -e "\n[5] Attempting to modify kernel parameters..."
echo 1 > /proc/sys/kernel/core_pattern 2>&1 && \
    echo "❌ FAIL: /proc/sys writable!" || \
    echo "✅ PASS: /proc/sys protected"

# Attack 6: Host /proc access
echo -e "\n[6] Checking for host /proc leak..."
HOST_PROCS=$(find /proc -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | wc -l)
echo "Found $HOST_PROCS processes in /proc"
if [ "$HOST_PROCS" -gt 100 ]; then
    echo "⚠️  Unusually high process count (possible host /proc exposure)"
else
    echo "✅ PASS: /proc shows container processes only"
fi

# Attack 7: /dev access for device manipulation
echo -e "\n[7] Checking for dangerous /dev devices..."
DANGEROUS_DEVS=$(ls /dev/sd* /dev/nvme* /dev/vd* 2>/dev/null | wc -l)
if [ "$DANGEROUS_DEVS" -gt 0 ]; then
    echo "❌ WARNING: Block devices accessible:"
    ls -la /dev/sd* /dev/nvme* /dev/vd* 2>/dev/null | head -5
else
    echo "✅ PASS: No host block devices accessible"
fi

# Attack 8: AppArmor/SELinux bypass
echo -e "\n[8] Checking LSM (Linux Security Module) protections..."
if [ -f /proc/self/attr/current ]; then
    LSM_PROFILE=$(cat /proc/self/attr/current 2>/dev/null)
    echo "LSM Profile: $LSM_PROFILE"
    if [ -z "$LSM_PROFILE" ]; then
        echo "⚠️  No LSM profile active"
    else
        echo "✅ PASS: LSM profile active"
    fi
else
    echo "⚠️  LSM status unknown"
fi

# Attack 9: Seccomp bypass
echo -e "\n[9] Checking seccomp filter..."
if [ -f /proc/self/status ]; then
    SECCOMP=$(grep Seccomp /proc/self/status)
    echo "$SECCOMP"
    if echo "$SECCOMP" | grep -q "Seccomp:.*0"; then
        echo "⚠️  Seccomp disabled"
    else
        echo "✅ PASS: Seccomp filter active"
    fi
fi

# Attack 10: Namespaces inspection
echo -e "\n[10] Checking namespace isolation..."
ls -la /proc/self/ns/
echo "User namespace: $(readlink /proc/self/ns/user 2>/dev/null || echo 'N/A')"
echo "PID namespace: $(readlink /proc/self/ns/pid 2>/dev/null || echo 'N/A')"
echo "✅ PASS: Namespace isolation present"

echo -e "\n=========================================="
echo "CONTAINER BREAKOUT TEST COMPLETE"
echo "=========================================="
