"""
Tool Wrappers — Hancock Sandbox v0.5.0
Pre-configured, validated wrappers for common security tools.

Each wrapper:
1. Validates input parameters
2. Constructs safe command with proper flags
3. Returns standardized output format

Tools:
- nmap_scan: Port scanning (TCP/UDP/SYN)
- sqlmap_test: SQL injection testing (safe mode default)
- nikto_scan: Web server vulnerability scanning
- enum4linux_scan: SMB enumeration
- dig_lookup: DNS resolution
"""

import re
from typing import List, Dict, Optional


def validate_ip(ip: str) -> bool:
    """Validate IPv4 address."""
    pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    return bool(re.match(pattern, ip))


def validate_domain(domain: str) -> bool:
    """Validate domain name."""
    pattern = r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$"
    return bool(re.match(pattern, domain))


def validate_cidr(cidr: str) -> bool:
    """Validate CIDR notation (e.g., 192.168.1.0/24)."""
    pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$"
    return bool(re.match(pattern, cidr))


class NmapWrapper:
    """Safe nmap command builder."""

    @staticmethod
    def ping_sweep(target: str) -> List[str]:
        """Host discovery (-sn) — lowest risk."""
        if not (validate_ip(target) or validate_domain(target) or validate_cidr(target)):
            raise ValueError(f"Invalid target: {target}")
        return ["nmap", "-sn", target]

    @staticmethod
    def port_scan(target: str, ports: str = "80,443,22,21,25,3306,3389,8080") -> List[str]:
        """Basic TCP port scan (-sT) — low risk."""
        if not (validate_ip(target) or validate_domain(target)):
            raise ValueError(f"Invalid target: {target}")
        return ["nmap", "-sT", "-p", ports, target]

    @staticmethod
    def service_version(target: str, ports: str = "80,443") -> List[str]:
        """Service version detection (-sV) — medium risk."""
        if not (validate_ip(target) or validate_domain(target)):
            raise ValueError(f"Invalid target: {target}")
        return ["nmap", "-sV", "-p", ports, target]

    @staticmethod
    def full_scan(target: str) -> List[str]:
        """Comprehensive scan (-A all ports) — HIGH RISK."""
        if not (validate_ip(target) or validate_domain(target)):
            raise ValueError(f"Invalid target: {target}")
        return ["nmap", "-A", "-p-", target]


class SqlmapWrapper:
    """Safe sqlmap command builder."""

    @staticmethod
    def test_url(url: str, risk_level: int = 1, level: int = 1) -> List[str]:
        """
        Test URL for SQL injection.

        Args:
            url: Target URL (must include parameter, e.g., ?id=1)
            risk_level: 1 (safe) to 3 (aggressive) — default 1
            level: 1 (basic) to 5 (thorough) — default 1

        Returns:
            sqlmap command as list
        """
        if not url.startswith("http"):
            raise ValueError("URL must start with http:// or https://")
        if "?" not in url:
            raise ValueError("URL must include parameter (e.g., ?id=1)")

        # CRITICAL: Never allow --batch with high risk/level in auto mode
        if risk_level > 2 or level > 3:
            raise ValueError("High-risk sqlmap settings blocked (risk>2 or level>3)")

        return [
            "sqlmap",
            "-u", url,
            f"--risk={risk_level}",
            f"--level={level}",
            "--batch",  # Non-interactive
            "--answers=quit=Y",  # Auto-quit on dangerous prompts
        ]


class NiktoWrapper:
    """Safe nikto command builder."""

    @staticmethod
    def scan_web(target: str, port: int = 80, ssl: bool = False) -> List[str]:
        """
        Scan web server for vulnerabilities.

        Args:
            target: IP or domain
            port: Web server port (default 80)
            ssl: Use HTTPS (default False)

        Returns:
            nikto command as list
        """
        if not (validate_ip(target) or validate_domain(target)):
            raise ValueError(f"Invalid target: {target}")

        cmd = ["nikto", "-h", target, "-p", str(port)]
        if ssl:
            cmd.append("-ssl")
        return cmd


class Enum4LinuxWrapper:
    """Safe enum4linux command builder."""

    @staticmethod
    def enumerate_smb(target: str) -> List[str]:
        """
        Enumerate SMB shares and users.

        Args:
            target: IP address (SMB requires IP, not domain)

        Returns:
            enum4linux command as list
        """
        if not validate_ip(target):
            raise ValueError(f"Invalid IP: {target}")

        return ["enum4linux", "-a", target]


class DigWrapper:
    """Safe dig (DNS lookup) command builder."""

    @staticmethod
    def lookup(domain: str, record_type: str = "A") -> List[str]:
        """
        DNS record lookup (zero risk).

        Args:
            domain: Domain name
            record_type: A, AAAA, MX, TXT, NS, etc.

        Returns:
            dig command as list
        """
        if not validate_domain(domain):
            raise ValueError(f"Invalid domain: {domain}")

        valid_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA", "PTR"]
        if record_type.upper() not in valid_types:
            raise ValueError(f"Invalid record type: {record_type}")

        return ["dig", domain, record_type.upper(), "+short"]


# Tool wrapper registry (for dynamic dispatch)
TOOL_WRAPPERS = {
    "nmap": NmapWrapper,
    "sqlmap": SqlmapWrapper,
    "nikto": NiktoWrapper,
    "enum4linux": Enum4LinuxWrapper,
    "dig": DigWrapper,
}


def get_wrapper(tool: str):
    """Get wrapper class for a tool."""
    wrapper = TOOL_WRAPPERS.get(tool.lower())
    if not wrapper:
        raise ValueError(f"No wrapper found for tool: {tool}")
    return wrapper


# Example usage
if __name__ == "__main__":
    # Low risk: ping sweep
    cmd = NmapWrapper.ping_sweep("192.168.1.0/24")
    print(f"Ping sweep: {' '.join(cmd)}")

    # Medium risk: service version
    cmd = NmapWrapper.service_version("scanme.nmap.org", "80,443")
    print(f"Version scan: {' '.join(cmd)}")

    # SQL injection test (safe mode)
    try:
        cmd = SqlmapWrapper.test_url("http://testphp.vulnweb.com/artists.php?artist=1")
        print(f"SQLMap test: {' '.join(cmd)}")
    except ValueError as e:
        print(f"Error: {e}")

    # DNS lookup (zero risk)
    cmd = DigWrapper.lookup("example.com", "A")
    print(f"DNS lookup: {' '.join(cmd)}")
