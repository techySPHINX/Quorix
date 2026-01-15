#!/usr/bin/env python3
"""
Comprehensive Test Runner for Evently
Run all test categories and generate reports
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"{'=' * 80}\n")

    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"\n❌ {description} failed!")
        return False
    else:
        print(f"\n✅ {description} passed!")
        return True


def main():
    parser = argparse.ArgumentParser(description="Run Evently tests")
    parser.add_argument(
        "--category",
        choices=["all", "unit", "integration", "e2e", "security", "performance"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox"],
        default="chrome",
        help="Browser for E2E tests"
    )

    args = parser.parse_args()

    # Base pytest command
    pytest_cmd = "pytest"

    if args.verbose:
        pytest_cmd += " -v"

    if args.coverage:
        pytest_cmd += " --cov=app --cov-report=html --cov-report=term"

    if args.parallel:
        pytest_cmd += " -n auto"

    results = []

    # Type checking
    if args.category in ["all"]:
        results.append(run_command("mypy app/", "Type Checking"))

    # Linting
    if args.category in ["all"]:
        results.append(run_command("flake8 app/", "Linting"))
        results.append(run_command("black --check app/", "Code Formatting Check"))
        results.append(run_command("isort --check-only app/", "Import Sorting Check"))

    # Unit tests
    if args.category in ["all", "unit"]:
        cmd = f"{pytest_cmd} tests/ -m 'unit or not (integration or e2e or security)'"
        results.append(run_command(cmd, "Unit Tests"))

    # Integration tests
    if args.category in ["all", "integration"]:
        cmd = f"{pytest_cmd} tests/integration/ -m integration"
        results.append(run_command(cmd, "Integration Tests"))

    # E2E tests
    if args.category in ["all", "e2e"]:
        cmd = f"{pytest_cmd} tests/e2e/ -m e2e --browser={args.browser}"
        results.append(run_command(cmd, "End-to-End Tests"))

    # Security tests
    if args.category in ["all", "security"]:
        cmd = f"{pytest_cmd} tests/security/ -m security"
        results.append(run_command(cmd, "Security Tests"))

        # Additional security checks
        results.append(run_command("safety check", "Dependency Vulnerability Check"))
        results.append(run_command("bandit -r app/", "Security Linting"))

    # Performance tests
    if args.category in ["performance"]:
        print("\n" + "=" * 80)
        print("Performance Testing with Locust")
        print("=" * 80)
        print("\nTo run performance tests:")
        print("  locust -f tests/performance/locustfile.py --host http://localhost:8000")
        print("  Then open http://localhost:8089 in your browser")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if all(results):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
