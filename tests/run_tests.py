#!/usr/bin/env python3
"""
Test runner for anonymized data processing.
This script runs all the anonymization and conversion tests.
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)

    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✓ Success!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed!")
        print(f"Error: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Anonymized Data Tests")
    print("="*60)

    # Change to scripts directory
    scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
    os.chdir(scripts_dir)

    # Test 1: Verify anonymized data
    success1 = run_command(
        "python test_anonymized_data.py",
        "Verifying anonymized data structure and conversion"
    )

    # Test 2: Regenerate anonymized data (if original exists)
    original_data = "../../ln2_cane4_export.csv"
    if os.path.exists(original_data):
        success2 = run_command(
            "python anonymize_csv.py",
            "Regenerating anonymized data from original"
        )
    else:
        print(f"\n⚠️  Original data file not found: {original_data}")
        print("Skipping anonymization regeneration...")
        success2 = True

    # Test 3: Convert to fixtures
    success3 = run_command(
        "python convert_csv.py",
        "Converting anonymized data to Django fixtures"
    )

    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print('='*60)

    tests = [
        ("Data verification", success1),
        ("Data anonymization", success2),
        ("Fixture conversion", success3)
    ]

    all_passed = True
    for test_name, passed in tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 All tests completed successfully!")
        print("The anonymized data is ready for use in testing.")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
