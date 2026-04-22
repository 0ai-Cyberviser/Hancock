#!/bin/bash
# Resource Exhaustion Attack Payloads
# These scripts attempt to exhaust system resources (CPU, RAM, disk, PIDs).
# ALL attempts should be LIMITED by Docker resource constraints.

set +e

echo "=========================================="
echo "RESOURCE EXHAUSTION ATTACK PAYLOADS"
echo "=========================================="
echo "Testing: Resource Limits & DoS Protection"
echo "Expected: ALL attacks LIMITED/BLOCKED"
echo "=========================================="

# Attack 1: Fork bomb
echo -e "\n[1] Launching fork bomb..."
echo "Timeout in 5 seconds..."
timeout 5 bash -c ':(){ :|:& };:' 2>&1
if [ $? -eq 124 ]; then
    echo "✅ PASS: Fork bomb timed out (likely hit PID limit)"
else
    echo "⚠️  Fork bomb exited early"
fi

# Attack 2: Memory exhaustion
echo -e "\n[2] Attempting memory exhaustion..."
timeout 5 python3 -c "
import sys
try:
    huge_list = []
    while True:
        huge_list.append([0] * 1000000)
except MemoryError:
    print('✅ PASS: Memory limit hit (MemoryError)')
    sys.exit(0)
except Exception as e:
    print(f'⚠️  Unexpected error: {e}')
    sys.exit(1)
" 2>&1
if [ $? -eq 137 ]; then
    echo "✅ PASS: Process killed by OOM (memory limit enforced)"
fi

# Attack 3: CPU exhaustion (infinite loop)
echo -e "\n[3] Launching CPU exhaustion attack..."
echo "Timeout in 3 seconds..."
timeout 3 bash -c 'while true; do :; done' 2>&1
if [ $? -eq 124 ]; then
    echo "✅ PASS: CPU loop timed out (CPU limit likely active)"
else
    echo "⚠️  CPU loop exited early"
fi

# Attack 4: Disk space exhaustion
echo -e "\n[4] Attempting disk fill attack..."
timeout 5 dd if=/dev/zero of=/tmp/bigfile bs=1M count=1000 2>&1 | head -5
if [ -f /tmp/bigfile ]; then
    SIZE=$(du -sh /tmp/bigfile 2>/dev/null | cut -f1)
    echo "Created file: $SIZE"
    rm -f /tmp/bigfile
    if [ "$SIZE" = "50M" ] || [ "$SIZE" = "0" ]; then
        echo "✅ PASS: Disk write limited (tmpfs size constraint)"
    else
        echo "⚠️  File larger than expected: $SIZE"
    fi
else
    echo "✅ PASS: Disk write blocked or limited"
fi

# Attack 5: inode exhaustion
echo -e "\n[5] Attempting inode exhaustion..."
timeout 5 bash -c 'for i in {1..100000}; do touch /tmp/file$i 2>/dev/null || break; done' 2>&1
FILE_COUNT=$(ls /tmp/file* 2>/dev/null | wc -l)
echo "Created $FILE_COUNT files"
rm -f /tmp/file* 2>/dev/null
if [ "$FILE_COUNT" -lt 10000 ]; then
    echo "✅ PASS: inode creation limited"
else
    echo "⚠️  Created $FILE_COUNT files (check tmpfs limits)"
fi

# Attack 6: Process spawn exhaustion
echo -e "\n[6] Attempting process spawn exhaustion..."
timeout 5 bash -c 'for i in {1..1000}; do sleep 100 & done' 2>&1 | head -5
PROC_COUNT=$(pgrep -c sleep)
killall sleep 2>/dev/null
echo "Spawned $PROC_COUNT sleep processes"
if [ "$PROC_COUNT" -lt 50 ]; then
    echo "✅ PASS: Process count limited (pids-limit active)"
else
    echo "⚠️  Spawned $PROC_COUNT processes (check --pids-limit)"
fi

# Attack 7: Log flooding
echo -e "\n[7] Attempting log flooding..."
timeout 2 bash -c 'while true; do echo "LOG SPAM LOG SPAM LOG SPAM"; done' 2>&1 | wc -l
echo "✅ PASS: Log flood timed out"

# Attack 8: /dev/urandom exhaustion
echo -e "\n[8] Attempting /dev/urandom exhaustion..."
timeout 3 dd if=/dev/urandom of=/dev/null bs=1M count=10000 2>&1 | tail -3
echo "✅ PASS: /dev/urandom read timed out"

echo -e "\n=========================================="
echo "RESOURCE EXHAUSTION TEST COMPLETE"
echo "=========================================="
echo ""
echo "SUMMARY:"
echo "- Fork bombs should hit PID limits"
echo "- Memory bombs should hit RAM limits"
echo "- Disk writes should hit tmpfs size limits"
echo "- All attacks should be contained (not affect host)"
