"""
Hancock — Locust load test scenarios.

Simulates realistic user behaviour across all API endpoints.

Run:
    locust -f tests/load_test_locust.py --host http://localhost:5000 \\
           --users 100 --spawn-rate 10

Or headless:
    locust -f tests/load_test_locust.py --headless \\
           --host http://localhost:5000 \\
           --users 50 --spawn-rate 5 --run-time 60s
"""
from __future__ import annotations

import json
import random

try:
    from locust import HttpUser, TaskSet, task, between, events  # type: ignore
except ImportError:
    raise ImportError(
        "locust is required for load testing. Install with: pip install locust"
    )


# ── Sample payloads ───────────────────────────────────────────────────────────

ALERTS = [
    "Mimikatz.exe executed on DC01",
    "Suspicious PowerShell encoded command from user finance\\john",
    "Multiple failed logons from 192.168.1.50 — possible brute force",
    "WMI persistence mechanism detected on WORKSTATION-42",
    "DNS request to known C2 domain from LAPTOP-77",
]

HUNT_TARGETS = [
    "lateral movement via SMB",
    "credential dumping",
    "kerberoasting",
    "living off the land binaries (LOLBins)",
    "data exfiltration via DNS",
]

SIGMA_DESCRIPTIONS = [
    "PowerShell execution with encoded commands",
    "Remote service installation via sc.exe",
    "Scheduled task creation for persistence",
    "PsExec usage for lateral movement",
]

YARA_DESCRIPTIONS = [
    "Mimikatz credential dumper",
    "Cobalt Strike beacon",
    "Generic ransomware dropper",
    "Remote access trojan with keylogger",
]

IOC_INDICATORS = [
    "185.220.101.1",
    "malware.example.com",
    "d41d8cd98f00b204e9800998ecf8427e",
    "https://evil.example.com/payload.exe",
]


# ── Task sets ─────────────────────────────────────────────────────────────────

class HealthCheckTasks(TaskSet):
    @task(5)
    def health(self):
        self.client.get("/health")

    @task(1)
    def metrics(self):
        self.client.get("/metrics")


class ChatTasks(TaskSet):
    @task(3)
    def chat_auto(self):
        self.client.post("/v1/chat", json={
            "message": random.choice([
                "What is Log4Shell?",
                "Explain SSRF vulnerabilities",
                "How does ransomware encrypt files?",
                "What is a Golden Ticket attack?",
            ]),
            "mode": "auto",
        })

    @task(2)
    def chat_soc(self):
        self.client.post("/v1/chat", json={
            "message": "Explain the PICERL incident response framework",
            "mode": "soc",
        })

    @task(1)
    def ask(self):
        self.client.post("/v1/ask", json={
            "question": "What is CVE-2024-1234?",
        })


class TriageTasks(TaskSet):
    @task(3)
    def triage(self):
        self.client.post("/v1/triage", json={
            "alert": random.choice(ALERTS),
        })

    @task(2)
    def hunt(self):
        self.client.post("/v1/hunt", json={
            "target": random.choice(HUNT_TARGETS),
            "siem":   random.choice(["splunk", "elastic", "sentinel"]),
        })

    @task(1)
    def respond(self):
        self.client.post("/v1/respond", json={
            "incident": random.choice(["ransomware", "phishing", "insider threat", "APT"]),
        })


class DetectionEngineeringTasks(TaskSet):
    @task(2)
    def sigma(self):
        self.client.post("/v1/sigma", json={
            "description": random.choice(SIGMA_DESCRIPTIONS),
        })

    @task(2)
    def yara(self):
        self.client.post("/v1/yara", json={
            "description": random.choice(YARA_DESCRIPTIONS),
        })

    @task(1)
    def ioc(self):
        self.client.post("/v1/ioc", json={
            "indicator": random.choice(IOC_INDICATORS),
        })


# ── User profiles ─────────────────────────────────────────────────────────────

class SOCAnalystUser(HttpUser):
    """Simulates a SOC analyst using the triage and hunting endpoints."""
    tasks       = [HealthCheckTasks, TriageTasks]
    wait_time   = between(1, 3)
    weight      = 50


class SecurityEngineerUser(HttpUser):
    """Simulates a detection engineer writing Sigma/YARA rules."""
    tasks     = [DetectionEngineeringTasks, HealthCheckTasks]
    wait_time = between(2, 5)
    weight    = 30


class ChatUser(HttpUser):
    """Simulates a general user chatting with Hancock."""
    tasks     = [ChatTasks, HealthCheckTasks]
    wait_time = between(1, 4)
    weight    = 20
