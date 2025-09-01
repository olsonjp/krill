# Test Data and Scripts

This directory contains anonymized test data and scripts for the Krill project.

## Directory Structure

```
tests/
├── data/                    # Anonymized test data
│   └── anonymized_test_data.csv
├── fixtures/                # Django fixtures
│   └── sample_fixtures.json
├── scripts/                 # Processing scripts
│   ├── anonymize_csv.py     # Anonymization script
│   ├── convert_csv.py       # CSV to fixtures converter
│   ├── create_test_superuser.py  # Test superuser creation
│   └── test_anonymized_data.py  # Verification script
├── ANONYMIZATION_README.md  # Anonymization documentation
├── TESTING_TODO.md          # Testing tasks and TODO items
├── run_tests.py             # Test runner
└── README.md               # This file
```

## Quick Start

### Run All Tests
```bash
# Using the test runner directly
python tests/run_tests.py

# Or using the Makefile (recommended)
make test-data
```

This will:
1. Verify the anonymized data structure
2. Regenerate anonymized data (if original exists)
3. Convert data to Django fixtures
4. Provide a summary of all tests

### Individual Scripts

#### Verify Anonymized Data
```bash
# Direct script execution
cd tests/scripts
python test_anonymized_data.py

# Or using Makefile
make test-data
```

#### Generate Anonymized Data
```bash
# Direct script execution
cd tests/scripts
python anonymize_csv.py

# Or using Makefile
make test-data-gen
```

#### Convert to Django Fixtures
```bash
# Direct script execution
cd tests/scripts
python convert_csv.py

# Or using Makefile
make test-data-fixtures
```

#### Generate Everything
```bash
# Generate all test data and fixtures
make test-data-all
```

## Using Test Data in Django Tests

```python
from django.test import TestCase
from django.core.management import call_command

class SampleDataTestCase(TestCase):
    def setUp(self):
        # Load anonymized test data
        call_command('loaddata', 'tests/fixtures/sample_fixtures.json')
    
    def test_sample_creation(self):
        # Your test code here
        pass
```

## Setting Up Test Environment

```bash
# Setup test environment with anonymized data and superuser
make setup-test

# Reset test environment with anonymized data and superuser
make reset-test

# Load only the test data
make load-testdata

# Create test superuser only
make create-test-superuser
```

### Test Superuser Credentials

When using `setup-test` or `reset-test`, a test superuser is automatically created with these credentials:

- **Username**: `admin`
- **Password**: `admin`
- **Email**: `admin@test.com`

This superuser has full administrative privileges and can be used to access the Django admin interface.

## Data Overview

- **871 sample records** with full anonymization
- **67 unique cell lines** (anonymized from original)
- **10 unique experiments** (anonymized from original)
- **14 unique sources** (anonymized from original)
- **16 unique persons** (anonymized from original)
- **1,683 Django fixtures** generated

## Security

- All sensitive data has been anonymized
- Original data patterns are systematically replaced
- Safe for use in public repositories and CI/CD pipelines

## Files

- `anonymized_test_data.csv` - The main test dataset
- `sample_fixtures.json` - Django fixtures for database loading
- All scripts are documented and include error handling

## Documentation

- `ANONYMIZATION_README.md` - Detailed information about the anonymization process
- `TESTING_TODO.md` - Testing tasks and TODO items
