HANCOCK TEST SUITE - RECOMMENDED RUNNING PROCEDURES
====================================================

QUICK COMMANDS FOR COMMON WORKFLOWS
====================================

Fast Smoke Test (30 seconds):
  pytest tests/ -k "not performance" -x
  Use when: Making quick changes, need fast feedback

Full Test Suite (75 seconds):
  pytest tests/ -v --tb=short
  Use when: Before committing code, final validation

With Coverage Report (90 seconds):
  pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term-missing
  Use when: Measuring test coverage, release preparation

Test Specific Files:
  pytest tests/test_hancock_api.py -v               # API tests
  pytest tests/test_hancock_agent.py -v             # Agent tests
  pytest tests/test_performance.py -v               # Performance regression
  pytest tests/test_edge_cases_and_isolation.py -v # Edge cases (new)

Test Specific Test Classes:
  pytest tests/test_hancock_api.py::TestRateLimit -v
  pytest tests/test_edge_cases_and_isolation.py::TestRateLimitEdgeCases -v

DETECTING TEST ISSUES
====================

Looking for Flaky Tests:
  for i in {1..5}; do
    echo "Run $i:"
    pytest tests/test_hancock_api.py::TestRateLimit::test_stale_rate_limit_buckets_are_evicted -q
  done
  Expected: 5 consecutive PASS (this was flaky before fix)

Looking for Slow Tests:
  pytest tests/ --durations=10
  Shows: 10 slowest tests
  Action: If any >2s (except performance tests), investigate

Checking Performance Regression:
  pytest tests/test_performance.py -v
  Expected: All PASS
  If FAIL: Could indicate environmental issue (shared runner overhead)
  If >50s: Check LATENCY_SAMPLES configuration

Checking for Isolation Issues:
  pytest tests/test_edge_cases_and_isolation.py::TestEnvironmentVariableIsolation -v
  Expected: All PASS
  If FAIL: Environment cleanup issue between tests

PERFORMANCE METRICS TO TRACK
============================

1. Test Execution Time
   Target: < 80 seconds for full suite
   Current: ~77 seconds ✓
   Alert: If > 90 seconds

2. Flaky Test Pass Rate
   Target: > 99% pass rate
   Monitor: test_stale_rate_limit_buckets_are_evicted
   Alert: If < 95% on CI

3. Coverage Percentage
   Target: >= 85%
   Measure: make test-cov
   Alert: If decreased

4. Performance Test P50 Latency
   Target: < thresholds in LATENCY_TARGETS_MS
   Monitor: Each endpoint separately
   Alert: If any exceed targets by >10%

CONTINUOUS INTEGRATION SETUP
=============================

GitHub Actions Example:
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - run: pip install -r requirements-dev.txt
      - run: make test
        
      # Performance monitoring
      - run: pytest tests/test_performance.py --tb=short
      
      # Upload coverage
      - uses: codecov/codecov-action@v3
        if: always()
```

TROUBLESHOOTING COMMON ISSUES
=============================

Issue: "StopIteration" in test_stale_rate_limit_buckets_are_evicted
  Status: SHOULD NOT OCCUR (fixed in this audit)
  If occurs: Verify you have the latest code
  Resolution: Pull latest changes

Issue: Performance tests timeout (>2 minutes)
  Cause: Shared CI runner under heavy load
  Status: Acceptable (LATENCY_TARGETS allow for variance)
  Resolution: Check CI runner metrics, may need retry

Issue: test_api_key_isolation_between_tests fails
  Cause: Previous test didn't clean up os.environ
  Status: Indicates isolation problem
  Resolution: Check all tests use patch.dict() or monkeypatch

Issue: Coverage decreased
  Cause: New code without tests
  Resolution: Add tests for new code paths

Issue: "FAIL - Observed X outliers >= Y ms"
  Cause: Performance regression or slow runner
  Status: Check OUTLIER_ALLOWED_COUNT in test_performance.py
  Resolution: Review recent changes for performance issues

MAINTENANCE TASKS
=================

Weekly:
  - Run full test suite locally
  - Check CI metrics for failures

Monthly:
  - Review slow/flaky test trends
  - Update LATENCY_TARGETS if infrastructure changes
  - Run full coverage report

Quarterly:
  - Audit new tests for flakiness patterns
  - Review and update edge case tests
  - Performance baseline update

When Adding New Features:
  - Add corresponding edge case tests
  - Consider environment isolation needs
  - Benchmark if touching latency-critical paths

INTERPRETING TEST OUTPUT
========================

Passing Test Output:
  ✓ test_name PASSED                     # Good
  ✓ test_name PASSED [warm cache]        # Good
  
Warning Signs:
  ⚠ test_name PASSED [flaky retry 1]    # Need attention
  ⚠ test_name FAILED [timeout]           # Performance issue
  ✗ test_name FAILED [AssertionError]    # Bug found

Coverage Output:
  Name                      Stmts   Miss Cover
  ─────────────────────────────────────────
  hancock_agent.py            200    15   92%    Good (>85%)
  input_validator.py           50     2   96%    Excellent

Performance Test Output:
  "GET /health" p50=35.2ms p95=110.5ms  PASS  # All under targets
  "POST /v1/ask" p50=155.3ms p95=280.1ms FAIL  # Exceeded target

MONITORING DASHBOARD IDEAS
===========================

For CI/CD Integration:

1. Test Execution Time Graph
   Track: Test suite duration over time
   Alert: If trends > 90 seconds

2. Flakiness Rate
   Track: Pass rate of rate limit test
   Alert: If < 98%

3. Coverage Trend
   Track: Coverage % over time
   Alert: If decreases

4. Performance Regression
   Track: P50/P95 latency per endpoint
   Alert: If exceeds targets

5. Test Failure Distribution
   Track: Which tests fail most
   Action: Prioritize fixing most-failed tests

ROLLBACK PROCEDURE
==================

If New Tests Cause Issues:

1. Identify problematic test:
   pytest tests/test_edge_cases_and_isolation.py -v

2. Temporary disable:
   - Add @pytest.mark.skip to test method
   - Or delete/rename test file

3. Investigate offline:
   - Review test logic
   - Check for environmental assumptions
   - Verify mock configuration

4. Re-enable after fix:
   - Remove @pytest.mark.skip
   - Verify passes locally
   - Push to branch for CI validation

VERSION TRACKING
================

Test Suite Version: 1.1
- Base: Original Hancock test suite
- 1.0: Initial audit baseline (81s, 1 critical flaky test)
- 1.1: Applied fixes (77s, 0 critical flaky tests, +12 coverage)

Next Version Ideas:
- 1.2: Parallel test execution with pytest-xdist
- 1.3: Flaky test detection with pytest-rerunfailures
- 2.0: Performance benchmarking with pytest-benchmark

REFERENCES
==========

Documentation Files Created:
  - TEST_AUDIT_REPORT.md (detailed findings)
  - FIXES_APPLIED.md (before/after code)
  - TEST_AUDIT_SUMMARY.csv (quick reference)
  - AUDIT_SUMMARY.txt (executive summary)
  - test_audit.py (audit automation script)

Test Files Modified:
  - tests/test_hancock_api.py (1 fix)
  - tests/test_performance.py (2 optimizations)

Test Files Created:
  - tests/test_edge_cases_and_isolation.py (12 new tests)

Command Reference:
  make test                  # Run full test suite
  make test-cov              # With coverage
  pytest tests/ -v           # Verbose output
  pytest tests/ --durations  # Show timing
