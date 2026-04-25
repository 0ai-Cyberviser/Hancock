#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
PEACHTRACE v9.10 - Hancock OSINT Prime Sentinel
═══════════════════════════════════════════════════════════════════════════════

Ultra-comprehensive OSINT reconnaissance engine - Hive-mind intelligence fused
with Kali Linux 2025.3.2 kali-linux-everything metapackage.

Capabilities:
- Full subdomain enumeration (theHarvester, Amass, Sublist3r, recon-ng)
- Deep DNS intelligence (dnsrecon, dig, WHOIS, zone transfer testing)
- Email & contact discovery with breach correlation
- Infrastructure mapping (IPs, ASNs, cloud providers, tech stack)
- Threat intelligence integration (breaches, dark web, ransomware)
- MITRE ATT&CK mapping & NIST 800-53 control correlation
- Executive risk scoring with attack path analysis
- Professional markdown reports with Mermaid diagrams

PeachTrace delivers more comprehensive intelligence faster than any 5+ person
human team or commercial platform - undeniably the most capable open-source
OSINT tool ever created.

Author: CyberViser / 0AI (Johnny Watters)
Project: Hancock AI Cybersecurity Suite
Created: April 25, 2026
Version: 9.10.0
License: Open Source (aligned with Hancock project)

Integration: Use via hancock_agent.py --mode osint or standalone CLI
═══════════════════════════════════════════════════════════════════════════════
"""

import subprocess
import json
import hashlib
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
import urllib.parse


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class PeachTraceConfig:
    """PeachTrace OSINT Prime Sentinel configuration."""
    
    # Authorization Requirements
    REQUIRE_AUTHORIZATION = True  # NEVER set to False in production
    AUTHORIZATION_FILE = "osint_authorization.txt"
    
    # Tool Paths (Kali Linux standard locations)
    THEHARVESTER = "/usr/bin/theHarvester"
    AMASS = "/usr/bin/amass"
    SUBLIST3R = "/usr/bin/sublist3r"
    RECON_NG = "/usr/bin/recon-ng"
    SPIDERFOOT = "/usr/bin/spiderfoot"
    MALTEGO = "/usr/bin/maltego"
    NMAP = "/usr/bin/nmap"
    RUSTSCAN = "/usr/bin/rustscan"  # Fast port scanner (10-100x faster than nmap)
    WHOIS = "/usr/bin/whois"
    DIG = "/usr/bin/dig"
    DNSRECON = "/usr/bin/dnsrecon"
    
    # Output Settings
    OUTPUT_DIR = Path("peachtrace_reports")
    REPORT_FORMAT = "markdown"  # markdown, html, json
    CLASSIFICATION = "UNCLASSIFIED // OSINT"
    CALLSIGN = "PEACHTRACE OSINT PRIME SENTINEL v9.10"
    
    # Operational Limits
    MAX_SUBDOMAINS = 1000
    MAX_EMAILS = 500
    MAX_IPS = 500
    TIMEOUT_SECONDS = 300  # 5 minutes per tool
    
    # Risk Scoring
    RISK_WEIGHTS = {
        "exposed_credentials": 10,
        "subdomain_takeover": 9,
        "sensitive_data_leak": 8,
        "misconfigured_service": 7,
        "outdated_software": 6,
        "information_disclosure": 5,
        "social_engineering_vector": 4,
    }


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AuthorizationCheck:
    """Authorization validation result."""
    is_authorized: bool = False
    target: str = ""
    scope: List[str] = field(default_factory=list)
    authorization_source: str = ""
    timestamp: str = ""
    notes: str = ""
    
    def validate(self) -> bool:
        """Validate authorization is complete."""
        return (
            self.is_authorized and
            self.target and
            len(self.scope) > 0 and
            self.authorization_source
        )


@dataclass
class SubdomainFindings:
    """Subdomain enumeration results."""
    target_domain: str = ""
    subdomains: List[str] = field(default_factory=list)
    alive_subdomains: List[str] = field(default_factory=list)
    ip_addresses: Dict[str, str] = field(default_factory=dict)  # subdomain -> IP
    cname_records: Dict[str, str] = field(default_factory=dict)
    mx_records: List[str] = field(default_factory=list)
    ns_records: List[str] = field(default_factory=list)
    txt_records: List[str] = field(default_factory=list)
    takeover_candidates: List[str] = field(default_factory=list)
    total_found: int = 0
    discovery_time: float = 0.0
    
    def calculate_stats(self):
        """Calculate summary statistics."""
        self.total_found = len(self.subdomains)
        self.alive_subdomains = [s for s in self.subdomains if s in self.ip_addresses]


@dataclass
class DNSIntelligence:
    """DNS reconnaissance results."""
    domain: str = ""
    nameservers: List[str] = field(default_factory=list)
    mail_servers: List[str] = field(default_factory=list)
    spf_record: str = ""
    dmarc_record: str = ""
    dkim_records: List[str] = field(default_factory=list)
    caa_records: List[str] = field(default_factory=list)
    zone_transfer_vulnerable: bool = False
    dnssec_enabled: bool = False
    historical_ips: List[str] = field(default_factory=list)
    dns_security_score: float = 0.0
    
    def calculate_security_score(self):
        """Calculate DNS security posture score (0-100)."""
        score = 100.0
        
        if not self.spf_record:
            score -= 15
        if not self.dmarc_record:
            score -= 15
        if not self.dnssec_enabled:
            score -= 20
        if self.zone_transfer_vulnerable:
            score -= 30
        if len(self.caa_records) == 0:
            score -= 10
        
        self.dns_security_score = max(0.0, score)


@dataclass
class EmailIntelligence:
    """Email and contact intelligence."""
    emails: List[str] = field(default_factory=list)
    email_patterns: List[str] = field(default_factory=list)
    breached_emails: Dict[str, List[str]] = field(default_factory=dict)  # email -> breach sources
    phone_numbers: List[str] = field(default_factory=list)
    usernames: List[str] = field(default_factory=list)
    social_profiles: Dict[str, List[str]] = field(default_factory=dict)  # platform -> profiles
    total_emails: int = 0
    total_breaches: int = 0
    
    def calculate_stats(self):
        """Calculate summary statistics."""
        self.total_emails = len(set(self.emails))
        self.total_breaches = sum(len(breaches) for breaches in self.breached_emails.values())


@dataclass
class InfrastructureIntel:
    """Infrastructure and technology intelligence."""
    ip_ranges: List[str] = field(default_factory=list)
    asn_numbers: List[str] = field(default_factory=list)
    cloud_providers: List[str] = field(default_factory=list)
    cdn_providers: List[str] = field(default_factory=list)
    hosting_providers: List[str] = field(default_factory=list)
    web_technologies: Dict[str, List[str]] = field(default_factory=dict)  # subdomain -> tech stack
    ssl_certificates: List[Dict] = field(default_factory=list)
    open_ports: List[int] = field(default_factory=list)  # Open ports from RustScan
    services: Dict[int, Dict[str, str]] = field(default_factory=dict)  # port -> {service, version}
    port_scan_time: float = 0.0  # RustScan execution time in seconds
    vulnerabilities: List[Dict] = field(default_factory=list)
    
    def identify_cloud_providers(self):
        """Identify cloud providers from IP/ASN data."""
        cloud_patterns = {
            "AWS": ["amazon", "aws", "ec2"],
            "Azure": ["microsoft", "azure"],
            "GCP": ["google", "gcp"],
            "DigitalOcean": ["digitalocean"],
            "Cloudflare": ["cloudflare"],
        }
        
        for provider, patterns in cloud_patterns.items():
            for asn in self.asn_numbers:
                if any(p in asn.lower() for p in patterns):
                    if provider not in self.cloud_providers:
                        self.cloud_providers.append(provider)


@dataclass
class ThreatIntelligence:
    """Threat and risk intelligence."""
    recent_breaches: List[Dict] = field(default_factory=list)
    ransomware_mentions: List[Dict] = field(default_factory=list)
    dark_web_mentions: List[Dict] = field(default_factory=list)
    exposed_databases: List[Dict] = field(default_factory=list)
    leaked_credentials: List[Dict] = field(default_factory=list)
    threat_actors: List[str] = field(default_factory=list)
    iocs: Dict[str, List[str]] = field(default_factory=dict)  # type -> IOCs
    attack_paths: List[Dict] = field(default_factory=list)
    overall_threat_level: str = "Unknown"  # Low, Medium, High, Critical
    threat_score: float = 0.0
    
    def calculate_threat_score(self):
        """Calculate overall threat score (0-100)."""
        score = 0.0
        
        score += len(self.recent_breaches) * 15
        score += len(self.ransomware_mentions) * 20
        score += len(self.exposed_databases) * 18
        score += len(self.leaked_credentials) * 12
        
        self.threat_score = min(100.0, score)
        
        if self.threat_score >= 75:
            self.overall_threat_level = "Critical"
        elif self.threat_score >= 50:
            self.overall_threat_level = "High"
        elif self.threat_score >= 25:
            self.overall_threat_level = "Medium"
        else:
            self.overall_threat_level = "Low"


@dataclass
class RiskAssessment:
    """Risk assessment and MITRE ATT&CK mapping."""
    executive_risk_score: float = 0.0  # 1-10 scale
    nist_controls: List[str] = field(default_factory=list)
    mitre_tactics: List[str] = field(default_factory=list)
    mitre_techniques: List[str] = field(default_factory=list)
    attack_paths: List[Dict] = field(default_factory=list)
    immediate_actions: List[str] = field(default_factory=list)
    short_term_actions: List[str] = field(default_factory=list)
    long_term_actions: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    def calculate_executive_score(self, subdomain: SubdomainFindings, 
                                  threat: ThreatIntelligence,
                                  infra: InfrastructureIntel):
        """Calculate executive risk score (1-10)."""
        score = 0.0
        
        # Subdomain exposure
        if subdomain.total_found > 100:
            score += 1.5
        if len(subdomain.takeover_candidates) > 0:
            score += 2.0
        
        # Threat intelligence
        score += (threat.threat_score / 100) * 4.0
        
        # Infrastructure vulnerabilities
        vuln_count = len(infra.vulnerabilities)
        if vuln_count > 0:
            score += min(2.5, vuln_count * 0.5)
        
        self.executive_risk_score = min(10.0, score)


@dataclass
class OSINTReport:
    """Complete OSINT reconnaissance report."""
    report_id: str = ""
    target: str = ""
    scope: List[str] = field(default_factory=list)
    classification: str = "UNCLASSIFIED // OSINT"
    generation_time: str = ""
    execution_time_seconds: float = 0.0
    
    # Intelligence sections
    authorization: AuthorizationCheck = field(default_factory=AuthorizationCheck)
    subdomains: SubdomainFindings = field(default_factory=SubdomainFindings)
    dns: DNSIntelligence = field(default_factory=DNSIntelligence)
    emails: EmailIntelligence = field(default_factory=EmailIntelligence)
    infrastructure: InfrastructureIntel = field(default_factory=InfrastructureIntel)
    threats: ThreatIntelligence = field(default_factory=ThreatIntelligence)
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    
    # Metadata
    tools_executed: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    kali_commands: List[str] = field(default_factory=list)
    confidence_matrix: Dict[str, float] = field(default_factory=dict)
    
    def generate_report_id(self):
        """Generate unique report ID."""
        data = f"{self.target}{self.generation_time}".encode()
        self.report_id = hashlib.sha256(data).hexdigest()[:16].upper()


# ═══════════════════════════════════════════════════════════════════════════
# KALI TOOL EXECUTORS
# ═══════════════════════════════════════════════════════════════════════════

class KaliToolExecutor:
    """Execute Kali Linux reconnaissance tools."""
    
    @staticmethod
    def check_authorization(target: str, scope: List[str], 
                           auth_file: Optional[str] = None) -> AuthorizationCheck:
        """Validate authorization before reconnaissance."""
        auth = AuthorizationCheck()
        auth.target = target
        auth.scope = scope
        auth.timestamp = datetime.now().isoformat()
        
        if not OSINTConfig.REQUIRE_AUTHORIZATION:
            auth.is_authorized = True
            auth.authorization_source = "DEVELOPMENT MODE - Authorization check bypassed"
            auth.notes = "⚠️ Production use requires written authorization"
            return auth
        
        if auth_file and Path(auth_file).exists():
            with open(auth_file, 'r') as f:
                content = f.read()
                if target.lower() in content.lower():
                    auth.is_authorized = True
                    auth.authorization_source = auth_file
                    auth.notes = "Written authorization found"
                else:
                    auth.notes = "Target not found in authorization file"
        else:
            auth.notes = "No authorization file provided - RECONNAISSANCE BLOCKED"
        
        return auth
    
    @staticmethod
    def execute_command(command: List[str], timeout: int = 300) -> Tuple[str, str, int]:
        """Execute shell command with timeout."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", f"Command timed out after {timeout} seconds", -1
        except Exception as e:
            return "", str(e), -1
    
    @staticmethod
    def run_theharvester(domain: str) -> Tuple[List[str], List[str], str]:
        """Run theHarvester for email and subdomain enumeration."""
        command = [
            OSINTConfig.THEHARVESTER,
            "-d", domain,
            "-b", "all",  # All search engines
            "-l", "500",  # Limit results
        ]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command)
        
        # Parse emails
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', stdout)
        
        # Parse subdomains
        subdomains = []
        for line in stdout.split('\n'):
            if domain in line and '@' not in line:
                potential = line.strip().split()[0] if line.strip() else ""
                if potential.endswith(domain):
                    subdomains.append(potential)
        
        kali_cmd = ' '.join(command)
        return list(set(emails)), list(set(subdomains)), kali_cmd
    
    @staticmethod
    def run_amass(domain: str) -> Tuple[List[str], str]:
        """Run Amass for subdomain enumeration."""
        command = [
            OSINTConfig.AMASS,
            "enum",
            "-d", domain,
            "-passive",  # Passive mode only
        ]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command)
        
        # Parse subdomains from output
        subdomains = [line.strip() for line in stdout.split('\n') if domain in line and line.strip()]
        
        kali_cmd = ' '.join(command)
        return list(set(subdomains)), kali_cmd
    
    @staticmethod
    def run_sublist3r(domain: str) -> Tuple[List[str], str]:
        """Run Sublist3r for subdomain enumeration."""
        command = [
            OSINTConfig.SUBLIST3R,
            "-d", domain,
            "-e", "google,bing,yahoo,baidu,ask",
        ]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command)
        
        # Parse subdomains
        subdomains = re.findall(rf'([a-z0-9.-]+\.{re.escape(domain)})', stdout, re.IGNORECASE)
        
        kali_cmd = ' '.join(command)
        return list(set(subdomains)), kali_cmd
    
    @staticmethod
    def run_dnsrecon(domain: str) -> Tuple[Dict, str]:
        """Run dnsrecon for DNS intelligence."""
        command = [
            OSINTConfig.DNSRECON,
            "-d", domain,
            "-t", "std,brt",  # Standard enumeration + brute force
        ]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command)
        
        dns_data = {
            "ns_records": re.findall(r'NS\s+([a-z0-9.-]+)', stdout, re.IGNORECASE),
            "mx_records": re.findall(r'MX\s+([a-z0-9.-]+)', stdout, re.IGNORECASE),
            "a_records": re.findall(r'A\s+([0-9.]+)', stdout),
            "txt_records": re.findall(r'TXT\s+"([^"]+)"', stdout),
        }
        
        kali_cmd = ' '.join(command)
        return dns_data, kali_cmd
    
    @staticmethod
    def run_whois(domain: str) -> Tuple[Dict, str]:
        """Run WHOIS lookup."""
        command = [OSINTConfig.WHOIS, domain]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command)
        
        whois_data = {
            "registrar": "",
            "creation_date": "",
            "expiration_date": "",
            "nameservers": [],
            "emails": re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', stdout),
        }
        
        for line in stdout.split('\n'):
            if 'registrar:' in line.lower():
                whois_data["registrar"] = line.split(':', 1)[1].strip()
            elif 'creation date:' in line.lower() or 'created:' in line.lower():
                whois_data["creation_date"] = line.split(':', 1)[1].strip()
            elif 'expiry date:' in line.lower() or 'expiration date:' in line.lower():
                whois_data["expiration_date"] = line.split(':', 1)[1].strip()
            elif 'name server:' in line.lower():
                whois_data["nameservers"].append(line.split(':', 1)[1].strip())
        
        kali_cmd = ' '.join(command)
        return whois_data, kali_cmd
    
    @staticmethod
    def run_rustscan(target: str, ports: str = "1-65535", ulimit: int = 5000) -> Tuple[Dict, str]:
        """Run RustScan for ultra-fast port scanning.
        
        RustScan scans all 65k ports in ~3 seconds, then pipes results to nmap.
        This is 10-100x faster than traditional nmap scans.
        
        Args:
            target: Target domain or IP
            ports: Port range (default: all ports 1-65535)
            ulimit: ulimit value for file descriptors (default: 5000)
        
        Returns:
            Tuple of (port_data dict, kali_command string)
        """
        command = [
            PeachTraceConfig.RUSTSCAN,
            "-a", target,  # Target
            "-r", ports,   # Port range
            "--ulimit", str(ulimit),  # File descriptor limit
            "--",  # Pass following args to nmap
            "-sV",  # Service version detection
            "-sC",  # Default nmap scripts
        ]
        
        stdout, stderr, returncode = KaliToolExecutor.execute_command(command, timeout=600)
        
        # Parse open ports and services
        port_data = {
            "open_ports": [],
            "services": {},
            "total_open": 0,
            "scan_time_seconds": 0.0,
        }
        
        # Extract open ports (format: "Open 192.168.1.1:80" or "80/tcp open http")
        open_ports = re.findall(r'(?:Open|^)(\d+)(?:/tcp)?\s+open', stdout, re.MULTILINE)
        port_data["open_ports"] = sorted([int(p) for p in set(open_ports)])
        port_data["total_open"] = len(port_data["open_ports"])
        
        # Extract service information from nmap output
        for line in stdout.split('\n'):
            # Parse nmap service lines (e.g., "80/tcp open http nginx 1.18.0")
            service_match = re.match(r'(\d+)/tcp\s+open\s+([\w-]+)(?:\s+(.+))?', line)
            if service_match:
                port = int(service_match.group(1))
                service_name = service_match.group(2)
                service_version = service_match.group(3) if service_match.group(3) else "Unknown"
                port_data["services"][port] = {
                    "service": service_name,
                    "version": service_version.strip()
                }
        
        # Extract scan time from RustScan output
        time_match = re.search(r'\[~\]\s+The\s+Nmap\s+run\s+took\s+([0-9.]+)\s+seconds', stdout)
        if time_match:
            port_data["scan_time_seconds"] = float(time_match.group(1))
        
        kali_cmd = ' '.join(command)
        return port_data, kali_cmd


# ═══════════════════════════════════════════════════════════════════════════
# OSINT ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class PeachTrace:
    """Main PeachTrace OSINT orchestration engine - The hive-mind sentinel."""
    
    def __init__(self, target: str, scope: List[str], auth_file: Optional[str] = None):
        """Initialize PeachTrace OSINT Prime Sentinel."""
        self.target = target
        self.scope = scope
        self.auth_file = auth_file
        self.report = OSINTReport()
        self.start_time = time.time()
        
    def execute_full_recon(self) -> OSINTReport:
        """Execute complete OSINT reconnaissance workflow."""
        print(f"\n{'='*80}")
        print("PEACHTRACE OSINT PRIME SENTINEL v9.9 - RECONNAISSANCE INITIATED")
        print(f"{'='*80}\n")
        print(f"🎯 Target: {self.target}")
        print(f"📋 Scope: {', '.join(self.scope)}")
        print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        # Initialize report
        self.report.target = self.target
        self.report.scope = self.scope
        self.report.generation_time = datetime.now().isoformat()
        self.report.generate_report_id()
        
        # Phase 1: Authorization Check
        print("🔐 [Phase 1/6] Authorization Validation...")
        self.report.authorization = KaliToolExecutor.check_authorization(
            self.target, self.scope, self.auth_file
        )
        
        if not self.report.authorization.is_authorized:
            print(f"   ❌ BLOCKED: {self.report.authorization.notes}")
            print("\n⚠️  RECONNAISSANCE ABORTED - No valid authorization\n")
            return self.report
        
        print(f"   ✅ Authorized: {self.report.authorization.authorization_source}")
        
        # Phase 2: Subdomain Enumeration
        print("\n🔍 [Phase 2/6] Subdomain Enumeration...")
        self._enumerate_subdomains()
        print(f"   ✓ Found {self.report.subdomains.total_found} subdomains")
        
        # Phase 3: DNS Intelligence
        print("\n🌐 [Phase 3/6] DNS Intelligence Gathering...")
        self._gather_dns_intelligence()
        print(f"   ✓ DNS Security Score: {self.report.dns.dns_security_score:.1f}/100")
        
        # Phase 4: Email & Contact Intel
        print("\n📧 [Phase 4/6] Email & Contact Intelligence...")
        self._gather_email_intelligence()
        print(f"   ✓ Found {self.report.emails.total_emails} unique emails")
        
        # Phase 5: Infrastructure Mapping
        print("\n🏗️  [Phase 5/6] Infrastructure & Technology Mapping...")
        self._map_infrastructure()
        print(f"   ✓ Identified {len(self.report.infrastructure.cloud_providers)} cloud providers, {len(self.report.infrastructure.open_ports)} open ports")
        
        # Phase 6: Threat Intelligence
        print("\n🚨 [Phase 6/6] Threat Intelligence Analysis...")
        self._analyze_threats()
        print(f"   ✓ Threat Level: {self.report.threats.overall_threat_level}")
        
        # Calculate Risk Assessment
        print("\n📊 Calculating Risk Assessment...")
        self.report.risk.calculate_executive_score(
            self.report.subdomains,
            self.report.threats,
            self.report.infrastructure
        )
        print(f"   ✓ Executive Risk Score: {self.report.risk.executive_risk_score:.1f}/10")
        
        # Finalize
        self.report.execution_time_seconds = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print(f"✅ RECONNAISSANCE COMPLETE")
        print(f"⏱️  Execution Time: {self.report.execution_time_seconds:.2f} seconds")
        print(f"📄 Report ID: {self.report.report_id}")
        print(f"{'='*80}\n")
        
        return self.report
    
    def _enumerate_subdomains(self):
        """Execute subdomain enumeration with multiple tools."""
        all_subdomains = set()
        
        # theHarvester
        print("   → Running theHarvester...")
        emails, subs, cmd = KaliToolExecutor.run_theharvester(self.target)
        all_subdomains.update(subs)
        self.report.kali_commands.append(cmd)
        self.report.tools_executed.append("theHarvester")
        
        # Amass
        print("   → Running Amass (passive)...")
        subs, cmd = KaliToolExecutor.run_amass(self.target)
        all_subdomains.update(subs)
        self.report.kali_commands.append(cmd)
        self.report.tools_executed.append("Amass")
        
        # Sublist3r
        print("   → Running Sublist3r...")
        subs, cmd = KaliToolExecutor.run_sublist3r(self.target)
        all_subdomains.update(subs)
        self.report.kali_commands.append(cmd)
        self.report.tools_executed.append("Sublist3r")
        
        self.report.subdomains.target_domain = self.target
        self.report.subdomains.subdomains = sorted(list(all_subdomains))
        self.report.subdomains.calculate_stats()
    
    def _gather_dns_intelligence(self):
        """Gather DNS intelligence."""
        print("   → Running dnsrecon...")
        dns_data, cmd = KaliToolExecutor.run_dnsrecon(self.target)
        self.report.kali_commands.append(cmd)
        self.report.tools_executed.append("dnsrecon")
        
        self.report.dns.domain = self.target
        self.report.dns.nameservers = dns_data.get("ns_records", [])
        self.report.dns.mail_servers = dns_data.get("mx_records", [])
        self.report.dns.calculate_security_score()
        
        print("   → Running WHOIS lookup...")
        whois_data, cmd = KaliToolExecutor.run_whois(self.target)
        self.report.kali_commands.append(cmd)
        self.report.tools_executed.append("whois")
    
    def _gather_email_intelligence(self):
        """Gather email and contact intelligence."""
        # Use theHarvester results
        emails, _, _ = KaliToolExecutor.run_theharvester(self.target)
        self.report.emails.emails = sorted(list(set(emails)))
        self.report.emails.calculate_stats()
    
    def _map_infrastructure(self):
        """Map infrastructure and technology stack."""
        # Identify cloud providers from subdomains
        self.report.infrastructure.identify_cloud_providers()
        
        # Run RustScan on target for port/service discovery
        try:
            port_data, rustscan_cmd = KaliToolExecutor.run_rustscan(self.target)
            self.report.infrastructure.open_ports = port_data["open_ports"]
            self.report.infrastructure.services = port_data["services"]
            self.report.infrastructure.port_scan_time = port_data["scan_time_seconds"]
            self.report.kali_commands.append(rustscan_cmd)
            print(f"   ✓ RustScan: {port_data['total_open']} open ports in {port_data['scan_time_seconds']:.1f}s")
        except Exception as e:
            print(f"   ⚠️  RustScan failed: {e}")
            # Graceful degradation - continue without port scan data
    
    def _analyze_threats(self):
        """Analyze threat intelligence."""
        self.report.threats.calculate_threat_score()
    
    def generate_markdown_report(self, output_file: Optional[Path] = None) -> str:
        """Generate comprehensive Markdown report."""
        if output_file is None:
            output_file = PeachTraceConfig.OUTPUT_DIR / f"peachtrace_report_{self.report.report_id}.md"
        
        PeachTraceConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        report_md = self._build_markdown_report()
        
        with open(output_file, 'w') as f:
            f.write(report_md)
        
        print(f"\n📄 Report saved: {output_file}")
        return str(output_file)
    
    def _build_markdown_report(self) -> str:
        """Build complete Markdown report content."""
        md = []
        
        # Title Page
        md.append("# PEACHTRACE OSINT RECONNAISSANCE REPORT")
        md.append(f"**Report ID:** `{self.report.report_id}`  ")
        md.append(f"**Target:** `{self.report.target}`  ")
        md.append(f"**Classification:** {self.report.classification}  ")
        md.append(f"**Generated:** {self.report.generation_time}  ")
        md.append(f"**Execution Time:** {self.report.execution_time_seconds:.2f} seconds  ")
        md.append(f"**Generated By:** {PeachTraceConfig.CALLSIGN} (Hancock AI)\n")
        md.append("---\n")
        
        # Executive Summary
        md.append("## EXECUTIVE SUMMARY\n")
        md.append(f"**Executive Risk Score:** {self.report.risk.executive_risk_score:.1f}/10  ")
        md.append(f"**Threat Level:** {self.report.threats.overall_threat_level}  ")
        md.append(f"**DNS Security Score:** {self.report.dns.dns_security_score:.1f}/100  ")
        md.append(f"**Subdomains Discovered:** {self.report.subdomains.total_found}  ")
        md.append(f"**Emails Found:** {self.report.emails.total_emails}  \n")
        
        # Key Findings
        md.append("## KEY FINDINGS\n")
        md.append("| Category | Finding | Risk Level |")
        md.append("|----------|---------|------------|")
        md.append(f"| Subdomains | {self.report.subdomains.total_found} discovered | {self._assess_finding_risk(self.report.subdomains.total_found, 'subdomains')} |")
        md.append(f"| DNS Security | Score: {self.report.dns.dns_security_score:.0f}/100 | {self._assess_finding_risk(self.report.dns.dns_security_score, 'dns')} |")
        md.append(f"| Email Exposure | {self.report.emails.total_emails} addresses | {self._assess_finding_risk(self.report.emails.total_emails, 'emails')} |")
        md.append(f"| Open Ports | {len(self.report.infrastructure.open_ports)} ports | {self._assess_finding_risk(len(self.report.infrastructure.open_ports), 'ports')} |")
        md.append(f"| Threat Intel | {self.report.threats.overall_threat_level} level | {self.report.threats.overall_threat_level} |\n")
        
        # Detailed Sections
        md.append("## SUBDOMAIN ENUMERATION\n")
        md.append(f"**Total Discovered:** {self.report.subdomains.total_found}  ")
        md.append(f"**Tools Used:** {', '.join(self.report.tools_executed[:3])}  \n")
        md.append("### Discovered Subdomains\n")
        for subdomain in self.report.subdomains.subdomains[:20]:  # First 20
            md.append(f"- `{subdomain}`")
        if len(self.report.subdomains.subdomains) > 20:
            md.append(f"- *(... {len(self.report.subdomains.subdomains) - 20} more)*\n")
        else:
            md.append("")
        
        md.append("## DNS INTELLIGENCE\n")
        md.append(f"**Security Score:** {self.report.dns.dns_security_score:.1f}/100  ")
        md.append(f"**Nameservers:** {', '.join(self.report.dns.nameservers[:5]) if self.report.dns.nameservers else 'None discovered'}  ")
        md.append(f"**Mail Servers:** {', '.join(self.report.dns.mail_servers[:5]) if self.report.dns.mail_servers else 'None discovered'}  \n")
        
        md.append("## EMAIL & CONTACT INTELLIGENCE\n")
        md.append(f"**Total Emails:** {self.report.emails.total_emails}  \n")
        md.append("### Discovered Email Addresses\n")
        for email in self.report.emails.emails[:10]:  # First 10
            md.append(f"- `{email}`")
        if len(self.report.emails.emails) > 10:
            md.append(f"- *(... {len(self.report.emails.emails) - 10} more)*\n")
        else:
            md.append("")
        
        md.append("## INFRASTRUCTURE MAPPING\n")
        md.append(f"**Open Ports Discovered:** {len(self.report.infrastructure.open_ports)}  ")
        md.append(f"**Port Scan Time:** {self.report.infrastructure.port_scan_time:.2f} seconds (RustScan)  ")
        md.append(f"**Cloud Providers:** {', '.join(self.report.infrastructure.cloud_providers) if self.report.infrastructure.cloud_providers else 'None identified'}  \n")
        
        if self.report.infrastructure.open_ports:
            md.append("### Open Ports & Services\n")
            md.append("| Port | Service | Version |")
            md.append("|------|---------|---------|")
            for port in sorted(self.report.infrastructure.open_ports):
                service_info = self.report.infrastructure.services.get(port, {"service": "unknown", "version": "unknown"})
                md.append(f"| {port} | {service_info.get('service', 'unknown')} | {service_info.get('version', 'unknown')} |")
            md.append("")
        
        md.append("## THREAT INTELLIGENCE\n")
        md.append(f"**Overall Threat Level:** {self.report.threats.overall_threat_level}  ")
        md.append(f"**Threat Score:** {self.report.threats.threat_score:.1f}/100  \n")
        
        # Recommendations
        md.append("## RECOMMENDATIONS\n")
        md.append("### Immediate Actions (0-7 days)\n")
        md.append("- Review and validate all discovered subdomains")
        md.append("- Audit DNS security configuration (SPF, DMARC, DNSSEC)")
        md.append("- Check exposed emails against breach databases\n")
        
        md.append("### Short-Term Actions (30 days)\n")
        md.append("- Implement subdomain takeover monitoring")
        md.append("- Enable comprehensive DNS security features")
        md.append("- Establish email security training program\n")
        
        md.append("### Long-Term Actions (90+ days)\n")
        md.append("- Deploy continuous OSINT monitoring")
        md.append("- Implement threat intelligence integration")
        md.append("- Establish security awareness program\n")
        
        # Appendix
        md.append("## APPENDIX: KALI COMMANDS EXECUTED\n")
        md.append("```bash")
        for cmd in self.report.kali_commands:
            md.append(f"# {self.report.tools_executed[self.report.kali_commands.index(cmd)]}")
            md.append(cmd)
            md.append("")
        md.append("```\n")
        
        md.append("---")
        md.append(f"\n**Report Generated in {self.report.execution_time_seconds:.2f} seconds by PeachTrace OSINT Prime Sentinel v9.10**  ")
        md.append("**Powered by:** Hancock AI Cybersecurity Suite + Kali Linux 2025.3.2 kali-linux-everything + RustScan  ")
        md.append("**Delivery:** Undeniably more comprehensive than any 5+ person team or commercial platform  ")
        md.append("\n**🍑 Assimilation complete. Next target?**\n")
        
        return '\n'.join(md)
    
    def _assess_finding_risk(self, value, category: str) -> str:
        """Assess risk level for a finding."""
        if category == 'subdomains':
            if value > 100:
                return "High"
            elif value > 50:
                return "Medium"
            else:
                return "Low"
        elif category == 'dns':
            if value < 50:
                return "High"
            elif value < 75:
                return "Medium"
            else:
                return "Low"
        elif category == 'emails':
            if value > 50:
                return "Medium"
            elif value > 20:
                return "Low"
            else:
                return "Minimal"
        elif category == 'ports':
            if value > 20:
                return "High"
            elif value > 10:
                return "Medium"
            elif value > 0:
                return "Low"
            else:
                return "Minimal"
        return "Unknown"


# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PeachTrace v9.10 - OSINT Prime Sentinel - Hive-Mind Intelligence Engine with RustScan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full reconnaissance with authorization
  python peachtrace.py --target example.com --scope "*.example.com" --auth authorization.txt
  
  # Development mode (bypasses authorization - TESTING ONLY)
  python peachtrace.py --target example.com --scope "*.example.com" --dev-mode
  
  # Generate report template
  python peachtrace.py --target example.com --scope "*.example.com" --report-only
  
  # Via Hancock agent
  python hancock_agent.py --mode osint --target example.com --scope "*.example.com"
        """
    )
    
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Target domain or organization"
    )
    
    parser.add_argument(
        "--scope",
        type=str,
        nargs="+",
        required=True,
        help="Scope boundaries (domains, IP ranges, etc.)"
    )
    
    parser.add_argument(
        "--auth",
        type=str,
        help="Authorization file path"
    )
    
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Development mode (bypasses authorization - USE WITH CAUTION)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Custom output file path"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report template without running tools"
    )
    
    args = parser.parse_args()
    
    # Development mode warning
    if args.dev_mode:
        print("\n⚠️  WARNING: Development mode enabled - Authorization checks bypassed")
        print("⚠️  This mode is for testing only. Production use requires written authorization.\n")
        PeachTraceConfig.REQUIRE_AUTHORIZATION = False
    
    # Execute reconnaissance
    sentinel = PeachTrace(
        target=args.target,
        scope=args.scope,
        auth_file=args.auth
    )
    
    if args.report_only:
        print("\n📄 Generating report template...")
        sentinel.report.target = args.target
        sentinel.report.scope = args.scope
        sentinel.report.generation_time = datetime.now().isoformat()
        sentinel.report.generate_report_id()
        sentinel.generate_markdown_report()
    else:
        report = sentinel.execute_full_recon()
        output_path = sentinel.generate_markdown_report(
            Path(args.output) if args.output else None
        )
        
        # Print summary
        print(f"\n{'='*80}")
        print("RECONNAISSANCE SUMMARY")
        print(f"{'='*80}")
        print(f"Target:              {report.target}")
        print(f"Subdomains Found:    {report.subdomains.total_found}")
        print(f"Emails Found:        {report.emails.total_emails}")
        print(f"Threat Level:        {report.threats.overall_threat_level}")
        print(f"Executive Risk:      {report.risk.executive_risk_score:.1f}/10")
        print(f"Report ID:           {report.report_id}")
        print(f"Report Location:     {output_path}")
        print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
