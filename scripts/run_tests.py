#!/usr/bin/env python3
"""
Test runner script for AutoNotion dual deployment.
Supports running tests for Azure Functions, Vercel, and shared components.
"""
import sys
import subprocess
import argparse

def run_tests(test_type="all", verbose=False):
    """Run tests based on the specified type."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Add markers based on test type
    if test_type == "azure":
        cmd.extend(["-m", "azure or not (vercel or shared)"])
    elif test_type == "vercel":
        cmd.extend(["-m", "vercel or shared"])
    elif test_type == "shared":
        cmd.extend(["-m", "shared"])
    elif test_type == "flask":
        # Run Flask-specific tests
        cmd.extend([
            "tests/integration/test_vercel_api_routes.py",
            "tests/integration/test_flask_logging.py",
            "tests/integration/test_shared_service_integration.py"
        ])
    elif test_type == "new":
        # Run only the new tests we created
        cmd.extend([
            "tests/unit/test_shared_service.py",
            "tests/integration/test_vercel_api_routes.py", 
            "tests/integration/test_dual_deployment.py",
            "tests/integration/test_flask_logging.py",
            "tests/integration/test_shared_service_integration.py"
        ])
    elif test_type == "all":
        # Run all tests
        pass
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    # Add test directory
    cmd.append("tests/")
    
    print(f"Running tests: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest: pip install pytest")
        return False

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Run AutoNotion tests")
    parser.add_argument(
        "--type", 
        choices=["all", "azure", "vercel", "shared", "flask", "new"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    args = parser.parse_args()
    
    success = run_tests(args.type, args.verbose)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
