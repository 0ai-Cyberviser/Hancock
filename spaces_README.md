---
title: Hancock — CyberViser AI Security Agent
emoji: 🛡️
colorFrom: green
colorTo: cyan
sdk: gradio
sdk_version: "4.44.0"
app_file: spaces_app.py
pinned: true
license: other
tags:
  - cybersecurity
  - pentest
  - soc
  - mitre-attack
  - mistral
  - security
---

# 🛡️ Hancock — AI Cybersecurity Agent

> **by [CyberViser](https://0ai-cyberviser.github.io/0ai/)** — Mistral 7B fine-tuned on MITRE ATT&CK, NVD/CVE, CISA KEV, and Atomic Red Team data.

## Modes

| Tab | What it does |
|-----|-------------|
| 🔵 SOC Triage | MITRE ATT&CK alert classification |
| 🔴 Pentest / CVE | Recon, exploitation, CVE analysis |
| 🎯 Threat Hunting | SIEM query generation (Splunk/Elastic/Sentinel) |
| 💻 Security Code | YARA, Sigma, KQL, SPL, Python, Bash |
| 👔 CISO Advisor | Risk, compliance, board reporting |
| 🔍 Sigma Rules | Sigma detection rule authoring |
| 🚨 IR Playbook | PICERL incident response |
| 🦠 YARA Rules | YARA malware detection rule authoring |
| 🔎 IOC Enrichment | Threat intelligence for IPs, domains, hashes |

## Setup

Set two Space Secrets (`Settings → Variables and secrets`):
- `HANCOCK_API_URL` — your Hancock API URL (Oracle Cloud VM or elsewhere)
- `HANCOCK_API_KEY` — Bearer token (`HANCOCK_API_KEY` from your `.env`)

## Links

- 🌐 [Portfolio Hub](https://0ai-cyberviser.github.io/0ai/)
- 📖 [Docs](https://github.com/cyberviser/Hancock/tree/main/docs)
- 💻 [GitHub](https://github.com/cyberviser/Hancock)
- 📧 0ai@cyberviserai.com
