#!/usr/bin/env python
"""
Test Suite Runner for Py Env Studio

Runs all test files in the tests directory and generates a comprehensive report.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def run_test_file(test_file):
    """Run a single test file and return results."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Running: {test_file.name}{Colors.RESET}")
    print(f"{'-'*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=False,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}Test timeout!{Colors.RESET}")
        return False
    except Exception as e:
        print(f"{Colors.RED}Error running test: {e}{Colors.RESET}")
        return False

def main():
    """Main test runner."""
    tests_dir = Path(__file__).parent
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Py Env Studio - Test Suite Runner{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"Test Directory: {tests_dir}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find all test files
    test_files = sorted([
        f for f in tests_dir.glob('test_*.py')
        if f.is_file() and f.name != 'test_suite_runner.py'
    ])
    
    if not test_files:
        print(f"{Colors.YELLOW}No test files found!{Colors.RESET}")
        return 1
    
    print(f"Found {len(test_files)} test file(s):")
    for tf in test_files:
        print(f"  - {tf.name}")
    
    # Run tests
    results = {}
    for test_file in test_files:
        success = run_test_file(test_file)
        results[test_file.name] = success
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for test_name, success in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if success else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status}: {test_name}")
    
    print(f"\n{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"Total: {len(results)}")
    
    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
