from __future__ import annotations
import shlex
import subprocess

class OrchestrationController:
    def __init__(self, allowlist=None):
        self.allowlist = set(allowlist or ["nmap", "sqlmap", "google_readonly"])

    def execute(self, tool_name: str, params: dict = None):
        if tool_name not in self.allowlist:
            return {"status": "blocked", "error": f"Tool {tool_name} not allowed"}
        print(f"✅ Executing {tool_name} in sandbox")
        return {"status": "success", "result": f"Executed {tool_name}"}

# Alias for import
OrchestrationController = OrchestrationController
