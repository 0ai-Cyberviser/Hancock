#!/usr/bin/env python3
"""
Test audit report generator for Hancock test suite.
Analyzes test files for flakiness, performance, and coverage gaps.
"""
import re
import os
from pathlib import Path
from collections import defaultdict

def parse_test_file(filepath):
    """Parse a test file and extract test methods."""
    with open(filepath, 'r') as f:
        content = f.read()

    tests = []
    # Find all test functions/methods
    pattern = r'def (test_\w+)\(.*?\):'
    for match in re.finditer(pattern, content):
        test_name = match.group(1)
        test_start = match.start()
        # Find the end of the test function
        lines_before = content[:test_start].count('\n')
        tests.append({
            'name': test_name,
            'line': lines_before + 1,
        })

    return tests

def analyze_for_flakiness(filepath):
    """Identify potential flaky test patterns."""
    with open(filepath, 'r') as f:
        content = f.read()

    issues = []

    # Check for time-dependent tests
    if 'time.time()' in content or 'time.sleep' in content or 'time.perf_counter' in content:
        if 'patch' in content and 'time' in content:
            issues.append({
                'type': 'time-dependent',
                'severity': 'high',
                'description': 'Test patches time.time() - may be fragile if call count varies',
            })

    # Check for order-dependent tests (database state, global state)
    if 'autouse=True' in content:
        issues.append({
            'type': 'shared-state',
            'severity': 'medium',
            'description': 'Uses autouse fixture - may have order dependencies',
        })

    # Check for thread/concurrency tests
    if 'ThreadPoolExecutor' in content or 'threading' in content:
        issues.append({
            'type': 'concurrency',
            'severity': 'medium',
            'description': 'Uses concurrent execution - potential race conditions',
        })

    return issues

def analyze_for_performance(filepath):
    """Identify slow tests."""
    with open(filepath, 'r') as f:
        content = f.read()

    issues = []

    # Check for high sample counts in performance tests
    pattern = r'_measure_ms\([^)]*n=(\d+)'
    for match in re.finditer(pattern, content):
        n_samples = int(match.group(1))
        if n_samples > 15:
            issues.append({
                'type': 'slow-test',
                'severity': 'medium',
                'description': f'Performance test with {n_samples} samples - will take >1s',
                'samples': n_samples,
            })

    # Check for high throughput batches
    pattern = r'THROUGHPUT_BATCH\s*=\s*(\d+)'
    for match in re.finditer(pattern, content):
        batch = int(match.group(1))
        if batch > 50:
            issues.append({
                'type': 'slow-throughput',
                'severity': 'low',
                'description': f'Throughput batch size of {batch} - may be slow',
                'batch': batch,
            })

    return issues

def analyze_for_coverage_gaps(filepath):
    """Identify coverage gaps."""
    with open(filepath, 'r') as f:
        content = f.read()

    issues = []

    # Check for missing error case tests
    endpoints_tested = set()
    pattern = r'def test_(\w+)\('
    for match in re.finditer(pattern, content):
        endpoints_tested.add(match.group(1))

    # Common error cases that might be missing
    error_cases = ['null', 'empty', 'oversized', 'malformed', 'concurrent', 'race']
    endpoint_file = Path(filepath).name

    for error_case in error_cases:
        if not any(error_case in test for test in endpoints_tested):
            # This is a hint, not a definitive gap
            pass

    # Check for missing isolation tests
    if 'os.environ' in content:
        if 'monkeypatch' not in content and 'patch.dict(os.environ' not in content:
            issues.append({
                'type': 'isolation-gap',
                'severity': 'low',
                'description': 'Tests use os.environ but may not properly isolate changes',
            })

    return issues

def generate_report():
    """Generate comprehensive audit report."""
    tests_dir = Path('/home/_0ai_/Hancock-1/tests')
    test_files = sorted(tests_dir.glob('test_*.py'))

    total_tests = 0
    total_issues = defaultdict(list)
    file_stats = {}

    print("\n" + "="*80)
    print("HANCOCK TEST SUITE AUDIT REPORT")
    print("="*80 + "\n")

    for test_file in test_files:
        print(f"Analyzing: {test_file.name}")

        tests = parse_test_file(test_file)
        flakiness_issues = analyze_for_flakiness(str(test_file))
        perf_issues = analyze_for_performance(str(test_file))
        coverage_issues = analyze_for_coverage_gaps(str(test_file))

        all_issues = flakiness_issues + perf_issues + coverage_issues

        file_stats[test_file.name] = {
            'test_count': len(tests),
            'issues': all_issues,
        }

        total_tests += len(tests)
        for issue in all_issues:
            total_issues[issue['type']].append({
                'file': test_file.name,
                'issue': issue,
            })

        if all_issues:
            print(f"  ⚠️  Found {len(all_issues)} issue(s)")
            for issue in all_issues:
                print(f"    - [{issue['severity']}] {issue['type']}: {issue['description']}")
        else:
            print(f"  ✓ No issues found")
        print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total test files: {len(test_files)}")
    print(f"Total tests: {total_tests}")
    print(f"Total issues found: {sum(len(v) for v in total_issues.values())}")
    print()

    if total_issues:
        print("Issues by category:")
        for issue_type, issues in sorted(total_issues.items()):
            print(f"  {issue_type}: {len(issues)}")
            for issue_info in issues:
                print(f"    - {issue_info['file']}: {issue_info['issue']['description']}")
        print()

    return file_stats, total_issues

if __name__ == '__main__':
    file_stats, total_issues = generate_report()
