# 🍑 PEACHTRACE QUICK START GUIDE

**Get running in 5 minutes**

---

## ⚡ FASTEST PATH TO FIRST REPORT

### Step 1: Verify Installation

```bash
cd /home/_0ai_/Hancock-1

# Check PeachTrace exists
ls -lh peachtrace.py

# Expected: -rwxr-xr-x ... peachtrace.py

# Verify Kali tools (optional - graceful degradation if missing)
which theHarvester amass sublist3r dnsrecon whois
```

### Step 2: Run Your First Scan (Development Mode)

```bash
# Safe testing target (OWASP test site)
python peachtrace.py \
    --target testphp.vulnweb.com \
    --scope "*.vulnweb.com" \
    --dev-mode

# Expected output in ~60 seconds:
# ✅ Authorized: DEVELOPMENT MODE
# 🔍 [Phase 2/6] Subdomain Enumeration...
#    ✓ Found 12 subdomains
# 📊 Executive Risk Score: 4.2/10
# 📄 Report saved: peachtrace_reports/peachtrace_report_XXXXXXXX.md
```

### Step 3: View Your Report

```bash
# Open the generated report
cat peachtrace_reports/peachtrace_report_*.md

# Or copy to your desktop
cp peachtrace_reports/peachtrace_report_*.md ~/Desktop/my_first_osint_report.md
```

---

## 🎯 REAL-WORLD USAGE (WITH AUTHORIZATION)

### Step 1: Create Authorization File

```bash
# Copy template
cp osint_authorization_template.txt my_authorization.txt

# Edit with your target details
nano my_authorization.txt

# Required fields:
# - TARGET: actual.target.com
# - SCOPE: *.target.com, specific subnets
# - AUTHORIZED BY: Name, Title, Organization
# - DATE: YYYY-MM-DD
# - PURPOSE: Security assessment per contract XYZ
```

### Step 2: Execute Authorized Scan

```bash
python peachtrace.py \
    --target actual.target.com \
    --scope "*.target.com" "target.org" \
    --auth my_authorization.txt \
    --output custom_report_name.md

# Authorization will be validated before any reconnaissance
```

### Step 3: Deliver Report

```bash
# Report is ready for:
# - Executive briefing (risk scores + recommendations)
# - Technical team (full subdomain list + Kali commands)
# - Compliance audit (complete methodology + citations)

# Convert to PDF (optional)
pandoc custom_report_name.md -o custom_report_name.pdf
```

---

## 🧪 TESTING WORKFLOW

### Safe Targets for Testing (No Authorization Required)

```bash
# 1. OWASP Vulnerable Web App
python peachtrace.py --target testphp.vulnweb.com --scope "*.vulnweb.com" --dev-mode

# 2. Your own domains
python peachtrace.py --target mydomain.com --scope "*.mydomain.com" --dev-mode

# 3. Intentionally public test sites
python peachtrace.py --target scanme.nmap.org --scope "scanme.nmap.org" --dev-mode
```

---

## 🔧 TROUBLESHOOTING

### "Command not found" errors

```bash
# Install missing Kali tools
sudo apt update && sudo apt install -y \
    theharvester \
    amass \
    sublist3r \
    dnsrecon \
    whois \
    dig

# Or use Docker with Kali image
docker run -it --rm \
    -v /home/_0ai_/Hancock-1:/workspace \
    kalilinux/kali-dev \
    bash -c "cd /workspace && python peachtrace.py --target example.com --scope '*.example.com' --dev-mode"
```

### "Authorization check failed"

```bash
# Either:
# 1. Use --dev-mode for testing
python peachtrace.py --target test.com --scope "*.test.com" --dev-mode

# 2. Create valid authorization file
cp osint_authorization_template.txt my_auth.txt
# Edit my_auth.txt with your target
python peachtrace.py --target test.com --scope "*.test.com" --auth my_auth.txt
```

### "Tool timeout" errors

```bash
# Edit peachtrace.py line ~55:
# TIMEOUT_SECONDS = 600  # Increase from 300 to 600
```

---

## 📊 UNDERSTANDING YOUR REPORT

### Executive Risk Score (1-10)

- **1-3 (Low):** Minimal exposure, good security posture
- **4-6 (Medium):** Moderate risk, some improvements needed
- **7-8 (High):** Significant exposure, immediate action required
- **9-10 (Critical):** Severe risk, emergency response needed

### DNS Security Score (0-100)

- **80-100:** Excellent - All security features enabled
- **60-79:** Good - Minor improvements possible
- **40-59:** Fair - Multiple weaknesses present
- **0-39:** Poor - Critical DNS security gaps

### Threat Level

- **Low:** No active threats detected
- **Medium:** Minor exposure, routine monitoring
- **High:** Active threats or recent breaches
- **Critical:** Imminent risk, immediate response required

---

## 🚀 NEXT STEPS

1. **Integrate with Hancock Agent**
   ```bash
   python hancock_agent.py --mode osint --target example.com
   ```

2. **Automate Weekly Scans**
   ```bash
   # Add to crontab for weekly execution
   0 0 * * 0 cd /home/_0ai_/Hancock-1 && python peachtrace.py --target mycompany.com --scope "*.mycompany.com" --auth my_auth.txt
   ```

3. **Export to PeachTree for Fine-Tuning**
   ```bash
   python peachtrace.py --target example.com --export-peachtree /peachtree/datasets/osint_$(date +%Y%m%d).jsonl
   ```

4. **Contribute Enhancements**
   - Add new OSINT tools
   - Improve parsing algorithms
   - Enhance report visualizations
   - Submit PR to github.com/cyberviser/Hancock

---

## 📚 ADDITIONAL RESOURCES

- **Full Documentation:** [PEACHTRACE_README.md](PEACHTRACE_README.md)
- **Hancock Project:** https://github.com/cyberviser/Hancock
- **MITRE ATT&CK:** https://attack.mitre.org/
- **OWASP:** https://owasp.org/
- **Kali Linux Tools:** https://www.kali.org/tools/

---

**🍑 You're now ready to run world-class OSINT reconnaissance!**

**Assimilation complete. Next target?**

