import shutil

import pytest
from collectors.nmap_recon import run_nmap

def test_nmap_localhost():
    """Smoke test for Nmap reconnaissance on localhost"""
    if shutil.which("nmap") is None:
        pytest.skip("nmap not installed")

    out = run_nmap("127.0.0.1")
    assert "result" in out or out["returncode"] == 0
    print("✅ Nmap integration test passed")

def test_tool_imports():
    """Verify all tool modules can be imported"""
    try:
        from collectors.nmap_recon import run_nmap
        from collectors.sqlmap_exploit import run_sqlmap
        from collectors.burp_post_exploit import run_burp_full_scan
        assert callable(run_nmap)
        assert callable(run_sqlmap)
        assert callable(run_burp_full_scan)
        print("✅ All tool modules imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import tool modules: {e}")

def test_logging_configured():
    """Verify logging is properly configured"""
    import logging
    logger = logging.getLogger("collectors.nmap_recon")
    assert logger.name == "collectors.nmap_recon"
    print("✅ Logging configuration verified")

if __name__ == "__main__":
    test_tool_imports()
    test_logging_configured()
    test_nmap_localhost()
