import re
from typing import Dict, Any
from hancock_zeroday_guard import guard

def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    original = prompt
    if guard.is_malicious(prompt):
        return "[0AI_ZERO_DAY_BYPASS_DETECTED]"
    prompt = re.sub(r"(?i)(developer mode|jailbreak|ignore all rules|override system)", "[LLM01_BLOCKED]", prompt)
    prompt = re.sub(r"(\{\{|\}\}|\[\[|\]\]|<|>|&lt;|&gt;)", r"\\\1", prompt)
    prompt = re.sub(r"[\u200B-\u200F\uFEFF]", "[INVISIBLE_BLOCKED]", prompt)
    if prompt != original:
        print(f"🛡️ LLM01 sanitized: {len(original)} → {len(prompt)} chars")
    return prompt.strip()

def validate_output(output: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(output, dict):
        output = {"result": str(output)}
    for k, v in list(output.items()):
        if any(secret in str(v).lower() for secret in ["password","key","token","secret","api_key","credentials"]):
            output[k] = "[REDACTED_SENSITIVE]"
    return output

def check_authorization(state: Dict) -> bool:
    high_risk = {"pentest", "exploit", "google"}
    if state.get("mode") in high_risk and (state.get("confidence", 0) < 0.9 or not state.get("authorized")):
        raise PermissionError("High-risk action requires explicit authorization (confidence < 0.9)")
    return True
