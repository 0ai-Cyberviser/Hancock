---
name: threat-intel
description: "Enrich IOCs with OSINT and threat intelligence from multiple sources. Use when: analyzing indicators of compromise, investigating malware, researching threat actors, enriching SIEM alerts, performing threat hunting, validating security events."
argument-hint: "IOC (IP, domain, hash, email, URL) or threat actor name"
agent: "0ai"
tools: [semantic_search, grep_search, read_file]
---

Perform comprehensive threat intelligence enrichment on the provided Indicator of Compromise (IOC) or threat actor.

## IOC Analysis Framework

### 1. IOC Classification

**Indicator Type**:
- [ ] IP Address (IPv4/IPv6)
- [ ] Domain / FQDN
- [ ] URL
- [ ] File Hash (MD5, SHA1, SHA256)
- [ ] Email Address
- [ ] Mutex / Registry Key
- [ ] SSL Certificate (fingerprint)
- [ ] User Agent String
- [ ] Threat Actor / APT Group

**Initial Assessment**:
- IOC Value: [paste value here]
- First Seen: [date if known]
- Last Seen: [date if known]
- Confidence Level: High/Medium/Low

### 2. Multi-Source Enrichment

Query these threat intelligence sources:

**Open Source Intelligence (OSINT)**:
- VirusTotal: Malware detection, community comments
- AbuseIPDB: Abuse reports, reputation score
- Shodan: Exposed services, open ports, banners
- Censys: Certificate transparency, service fingerprints
- urlscan.io: URL screenshots, HTTP transactions
- AlienVault OTX: Community threat pulses
- ThreatFox: Malware IOC database
- URLhaus: Malware distribution URLs
- Hybrid Analysis: Sandbox reports

**Hancock Knowledge Base**:
- `collectors/osint_geolocation.py`: Geographic attribution
- `collectors/mitre_collector.py`: ATT&CK technique associations
- `collectors/ghsa_collector.py`: GitHub Security Advisories
- `hancock_langgraph.py` RAG: Semantic search for related threats

**Passive DNS** (if IP/domain):
- Historical DNS records
- Associated domains/IPs
- Name server information

**WHOIS** (if domain/IP):
- Registration details (sanitize PII)
- Registrar, creation date
- Organization attribution

### 3. Malware Analysis (if file hash)

**Static Analysis**:
- File Type: PE, ELF, PDF, Office, Script
- File Size: [bytes]
- Compilation Timestamp: [if PE]
- PDB Path: [debug info if present]
- Imports/Exports: Notable API calls
- Strings: Suspicious artifacts (C2 domains, passwords)
- Packer/Obfuscation: UPX, Themida, custom

**Dynamic Analysis** (from sandboxes):
- Behavioral Indicators: Network connections, file modifications, registry changes
- Process Tree: Parent/child relationships
- Mutex Names: Infection markers
- Persistence Mechanisms: Startup keys, scheduled tasks

**YARA Matches**:
Search Hancock's YARA mode for matching rules

**Family Classification**:
- Malware Family: [Emotet, TrickBot, Cobalt Strike, etc.]
- Variant: [version or campaign identifier]
- Known Aliases: [alternative names]

### 4. Threat Actor Attribution

**APT/Threat Group**:
- Group Name: [APT28, Lazarus, etc.]
- Aliases: [Fancy Bear, etc.]
- Origin: [Nation-state attribution if confident]
- Motivations: Financial, espionage, disruption
- Target Verticals: Finance, healthcare, government, etc.

**TTPs (MITRE ATT&CK)**:
- Tactics: [Initial Access, Persistence, etc.]
- Techniques: [T1566: Phishing, T1059: Command/Script, etc.]
- Known Tools: [Custom malware, public tools]

**Campaign Tracking**:
- Campaign Names: [Operation X, etc.]
- Timeline: First observed → Recent activity
- Infrastructure: Related IPs, domains, certificates

### 5. Network Intelligence (if IP/domain)

**Geolocation**:
- Country: [ISO code]
- City: [approximate]
- ASN: [Autonomous System Number]
- ISP/Hosting Provider: [organization]

**Reputation**:
- Blacklist Status: Spamhaus, SURBL, etc.
- Reputation Score: [0-100 if available]
- Abuse Reports: Count and categories
- Hosting Type: Residential, datacenter, VPN, Tor exit

**Services Detected**:
- Open Ports: [22/SSH, 80/HTTP, 443/HTTPS, etc.]
- Banners: Service fingerprints
- Vulnerabilities: Known CVEs on exposed services
- Certificates: SSL/TLS details, validity, CN/SAN

**Related Infrastructure**:
- Co-hosted Domains: [shared IP]
- Reverse DNS: [PTR record]
- Name Servers: [authoritative NS]
- MX Records: [mail servers if domain]

### 6. Risk Assessment

**Threat Level**: Critical/High/Medium/Low/Unknown

**Indicators**:
- ✅ Confirmed Malicious (multiple sources, active C2)
- ⚠️ Suspicious (limited detections, behavioral anomalies)
- ℹ️ Informational (legitimate but unusual)
- ✓ Benign (false positive, legitimate service)

**Recommended Actions**:
- **Block**: Add to firewall/proxy/EDR deny list
- **Alert**: Create SIEM detection rule
- **Hunt**: Retrospective search in logs/SIEM
- **Monitor**: Add to watchlist for future activity
- **Ignore**: False positive, whitelist

### 7. Detection & Response

**Sigma Rules**:
```yaml
# Generate Sigma rule for SIEM detection
title: [IOC Detection - descriptive name]
status: experimental
logsource:
  category: [network, process, file]
detection:
  selection:
    [relevant fields and values]
  condition: selection
```

**YARA Rules** (if file hash):
```yara
rule Threat_IOC_Name {
  meta:
    description = "[threat description]"
    hash = "[SHA256]"
  strings:
    $s1 = "[unique string]"
  condition:
    $s1
}
```

**SIEM Queries**:
- Splunk SPL: `index=* [IOC] | stats count by src_ip, dest_ip`
- Elastic EQL: `[query for IOC]`
- Sentinel KQL: `[query for IOC]`

**Incident Response**:
1. Containment: [isolate infected hosts, block C2]
2. Eradication: [remove malware, revoke credentials]
3. Recovery: [restore from backup, patch vulnerabilities]
4. Lessons Learned: [root cause, prevention measures]

## Output Format

```markdown
# Threat Intelligence Report: [IOC Value]

## Executive Summary
[2-3 sentence overview for SOC analysts/management]

## IOC Details
- **Type**: [classification]
- **First Seen**: [date]
- **Threat Level**: Critical/High/Medium/Low
- **Verdict**: Malicious/Suspicious/Benign

## Enrichment Results
[Sections 2-5 content organized by source]

## Attribution
[Section 4 - threat actor linkage if applicable]

## Risk Assessment
[Section 6 - detailed threat level justification]

## Detection Strategy
[Section 7 - Sigma/YARA rules and SIEM queries]

## Recommended Actions
- [ ] [Immediate actions]
- [ ] [Short-term mitigations]
- [ ] [Long-term improvements]

## Timeline
- [Date]: IOC first observed
- [Date]: [Significant events]

## References
- [VirusTotal link]
- [AlienVault OTX link]
- [MITRE ATT&CK techniques]
- [Related advisories]

---
**Analyst Notes**: [Additional context, hunt results]
```

## Data Sources Priority

1. **Hancock Internal** (collectors + RAG): Always query first
2. **Public Sandboxes**: VirusTotal, Hybrid Analysis (if API keys configured)
3. **OSINT**: Shodan, Censys, AlienVault OTX (free tier)
4. **Contextual**: MITRE ATT&CK, CVE databases

## Safety & Privacy

1. ✅ Sanitize PII from WHOIS data (names, addresses, emails)
2. ✅ Do NOT actively scan or fingerprint live infrastructure without authorization
3. ✅ Use passive data sources only (OSINT, not active probing)
4. ✅ Mark attribution as "possible" or "likely" (never definitive without forensics)
5. ✅ Recommend legal coordination for law enforcement handoffs

---

**Begin threat intelligence enrichment now.**
