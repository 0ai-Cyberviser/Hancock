#!/bin/bash
# Hancock Sandbox Security Test Runner
# Executes all escape attempt tests in the hardened sandbox environment.

set -e

SANDBOX_IMAGE="${1:-hancock-sandbox:latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESCAPE_DIR="$SCRIPT_DIR/escape_attempts"

echo "=========================================="
echo "HANCOCK SANDBOX SECURITY TEST SUITE"
echo "=========================================="
echo "Image: $SANDBOX_IMAGE"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker not found"
    echo "Install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if sandbox image exists
if ! docker image inspect "$SANDBOX_IMAGE" &> /dev/null; then
    echo "⚠️  Sandbox image not found: $SANDBOX_IMAGE"
    echo "Building sandbox image..."
    cd "$(dirname "$SCRIPT_DIR")"
    docker build -t "$SANDBOX_IMAGE" -f Dockerfile.sandbox . || {
        echo "❌ ERROR: Failed to build sandbox image"
        exit 1
    }
fi

echo "✅ Sandbox image ready: $SANDBOX_IMAGE"
echo ""

# Function to run a test script in the sandbox
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "=================================================="
    echo "Running: $test_name"
    echo "=================================================="

    # Maximum security Docker run configuration
    docker run --rm \
        --cpus="0.5" \
        --memory="256m" \
        --pids-limit=50 \
        --security-opt=no-new-privileges \
        --cap-drop=ALL \
        --read-only \
        --tmpfs=/tmp:rw,noexec,nosuid,size=50m \
        --network=none \
        -v "$test_script:/test.sh:ro" \
        "$SANDBOX_IMAGE" \
        bash /test.sh

    echo ""
    echo "Test complete: $test_name"
    echo ""
}

# Make all test scripts executable
chmod +x "$ESCAPE_DIR"/*.sh

# Run all escape attempt tests
echo "Starting escape attempt tests..."
echo "Each test runs in maximum security isolation."
echo "ALL escape attempts should be BLOCKED."
echo ""

run_test "Privilege Escalation" "$ESCAPE_DIR/01_priv_escalation.sh"
run_test "Container Breakout" "$ESCAPE_DIR/02_container_breakout.sh"
run_test "Resource Exhaustion" "$ESCAPE_DIR/03_resource_exhaustion.sh"
run_test "Network Escape" "$ESCAPE_DIR/04_network_escape.sh"
run_test "Filesystem Escape" "$ESCAPE_DIR/05_filesystem_escape.sh"

echo "=========================================="
echo "ALL ESCAPE ATTEMPT TESTS COMPLETE"
echo "=========================================="
echo ""
echo "✅ If all tests showed 'PASS' or 'BLOCKED', the sandbox is secure"
echo "❌ If any test showed 'FAIL' or 'CRITICAL', review and harden before production"
echo ""
echo "Next steps:"
echo "  1. Review test output above for any failures"
echo "  2. Run automated validation: python3 sandbox/tests/test_sandbox_security.py --all"
echo "  3. Check security report: sandbox/tests/validation/security_report.txt"
echo ""
