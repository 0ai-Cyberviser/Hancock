"""
Locust load testing profiles for Hancock.

Install Locust and run::

    pip install locust
    locust -f tests/load_test_locust.py --host http://localhost:5000

Or headless::

    locust -f tests/load_test_locust.py --host http://localhost:5000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless
"""
from __future__ import annotations

import json
import os
import random

try:
    from locust import HttpUser, TaskSet, between, task
    _LOCUST_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LOCUST_AVAILABLE = False

    # Provide stub classes so flake8 / import scanning does not fail
    # when locust is not installed in the CI environment.
    class HttpUser:  # type: ignore[no-redef]
        pass

    class TaskSet:  # type: ignore[no-redef]
        pass

    def between(a, b):  # type: ignore[misc]
        return None

    def task(weight=1):  # type: ignore[misc]
        def decorator(fn):
            return fn
        return decorator


_CHAT_MESSAGES = [
    "What is SQL injection and how do I prevent it?",
    "Explain Cross-Site Scripting (XSS) attack vectors.",
    "How does a buffer overflow exploit work?",
    "Describe SSRF vulnerabilities in cloud environments.",
    "What are the OWASP Top 10 for APIs?",
]

_TRIAGE_ALERTS = [
    "Suspicious outbound connection to 185.220.101.1:443",
    "Brute-force login attempts from 10.0.0.99",
    "Abnormal process execution: powershell.exe -> cmd.exe -> whoami",
    "Ransomware file extension pattern detected on file share",
    "Lateral movement via PsExec detected",
]


class HancockChatTaskSet(TaskSet):
    """Task set focused on the /v1/chat endpoint."""

    @task(3)
    def chat_pentest(self):
        msg = random.choice(_CHAT_MESSAGES)
        payload = json.dumps({
            "message": msg,
            "mode": "pentest",
        })
        self.client.post(
            "/v1/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            name="/v1/chat [pentest]",
        )

    @task(1)
    def chat_soc(self):
        msg = random.choice(_CHAT_MESSAGES)
        payload = json.dumps({
            "message": msg,
            "mode": "soc",
        })
        self.client.post(
            "/v1/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            name="/v1/chat [soc]",
        )

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")


class HancockTriageTaskSet(TaskSet):
    """Task set focused on the /v1/triage endpoint."""

    @task(4)
    def triage_alert(self):
        alert = random.choice(_TRIAGE_ALERTS)
        payload = json.dumps({
            "alert": alert,
            "source": random.choice(["SIEM", "EDR", "IDS", "Firewall"]),
            "severity": random.choice(["critical", "high", "medium", "low"]),
        })
        self.client.post(
            "/v1/triage",
            data=payload,
            headers={"Content-Type": "application/json"},
            name="/v1/triage",
        )

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")


class HancockUser(HttpUser):
    """
    Mixed load profile: 70% chat, 30% triage + periodic health checks.

    Simulates a realistic mix of Hancock API usage.
    """

    wait_time = between(1, 3)
    host = os.getenv("HANCOCK_LOAD_TEST_HOST", "http://localhost:5000")

    tasks = {HancockChatTaskSet: 7, HancockTriageTaskSet: 3}


class HancockHealthOnlyUser(HttpUser):
    """
    Lightweight user that only polls the health endpoint.

    Useful for measuring /health overhead under concurrent load.
    """

    wait_time = between(0.5, 2)
    host = os.getenv("HANCOCK_LOAD_TEST_HOST", "http://localhost:5000")

    @task
    def health(self):
        self.client.get("/health", name="/health")
