#!/usr/bin/env python3
"""
Test runner script for X-Ray system.

This script runs all tests and provides a comprehensive verification
of the X-Ray SDK and API functionality.
"""

import subprocess
import sys
import os
import time
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print(f"Command: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("❌ FAILED")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            if result.stdout:
                print("Standard output:")
                print(result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT - Command took too long")
        return False
    except Exception as e:
        print(f"❌ ERROR - {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi", "uvicorn", "sqlalchemy", "pydantic", "requests", "pytest"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def run_sdk_tests():
    """Run SDK unit tests."""
    return run_command(
        "python -m pytest tests/test_sdk.py -v",
        "Running SDK unit tests"
    )


def run_api_tests():
    """Run API tests."""
    return run_command(
        "python -m pytest tests/test_api.py -v",
        "Running API tests"
    )


def run_demo_script():
    """Run the demo script to verify end-to-end functionality."""
    print("\n🎬 Running demo script...")
    print("-" * 50)
    
    try:
        # Change to the correct directory
        original_dir = os.getcwd()
        os.chdir(Path(__file__).parent)
        
        # Run demo with automated input
        process = subprocess.Popen(
            [sys.executable, "demo.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send "1" to select first demo option
        stdout, stderr = process.communicate(input="1\n", timeout=30)
        
        os.chdir(original_dir)
        
        if process.returncode == 0:
            print("✅ Demo completed successfully")
            print("Demo output:")
            print(stdout)
            return True
        else:
            print("❌ Demo failed")
            if stderr:
                print("Error output:")
                print(stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Demo timed out")
        return False
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return False


def verify_project_structure():
    """Verify all required files are present."""
    print("\n📁 Verifying project structure...")
    
    required_files = [
        "README.md",
        "ARCHITECTURE.md",
        "requirements.txt",
        "demo.py",
        "sdk/setup.py",
        "sdk/xray_sdk/__init__.py",
        "sdk/xray_sdk/tracker.py",
        "sdk/xray_sdk/models.py",
        "api/main.py",
        "api/models.py",
        "api/database.py",
        "api/schemas.py",
        "api/crud.py",
        "tests/test_sdk.py",
        "tests/test_api.py",
        "examples/competitor_selection_example.py",
        "Dockerfile",
        "docker-compose.yml"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        return False
    
    return True


def run_syntax_checks():
    """Run basic syntax checks on Python files."""
    print("\n🔍 Running syntax checks...")
    
    python_files = [
        "demo.py",
        "sdk/xray_sdk/tracker.py",
        "sdk/xray_sdk/models.py",
        "api/main.py",
        "api/models.py",
        "api/database.py",
        "api/schemas.py",
        "api/crud.py",
        "tests/test_sdk.py",
        "tests/test_api.py",
        "examples/competitor_selection_example.py"
    ]
    
    all_valid = True
    
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                print(f"  ✅ {file_path}")
            except SyntaxError as e:
                print(f"  ❌ {file_path} - Syntax Error: {e}")
                all_valid = False
            except Exception as e:
                print(f"  ⚠️  {file_path} - Warning: {e}")
        else:
            print(f"  ❌ {file_path} - File not found")
            all_valid = False
    
    return all_valid


def main():
    """Run all tests and verifications."""
    print("🧪 X-Ray System Test Suite")
    print("=" * 60)
    print("This script verifies the complete X-Ray system implementation.")
    print()
    
    # Track test results
    results = {}
    
    # 1. Check project structure
    results["structure"] = verify_project_structure()
    
    # 2. Check syntax
    results["syntax"] = run_syntax_checks()
    
    # 3. Check dependencies
    results["dependencies"] = check_dependencies()
    
    # 4. Run SDK tests
    if results["dependencies"]:
        results["sdk_tests"] = run_sdk_tests()
    else:
        results["sdk_tests"] = False
        print("\n⏭️  Skipping SDK tests due to missing dependencies")
    
    # 5. Run API tests
    if results["dependencies"]:
        results["api_tests"] = run_api_tests()
    else:
        results["api_tests"] = False
        print("\n⏭️  Skipping API tests due to missing dependencies")
    
    # 6. Run demo
    if results["dependencies"] and results["syntax"]:
        results["demo"] = run_demo_script()
    else:
        results["demo"] = False
        print("\n⏭️  Skipping demo due to previous failures")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.upper():<15} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! The X-Ray system is ready for submission.")
        print("\nNext steps:")
        print("1. Record your video walkthrough (max 10 minutes)")
        print("2. Push code to GitHub repository")
        print("3. Submit via the provided form")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please fix issues before submission.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)