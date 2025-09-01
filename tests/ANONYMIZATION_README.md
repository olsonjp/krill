# Data Anonymization for Testing

This document describes the anonymization process used to create test data from the original biological sample dataset.

## Overview

The original dataset (`ln2_cane4_export.csv`) contains sensitive biological sample data including:
- Cell line names (e.g., "MDA MB 134VI", "SUM44PE")
- Personal identifiers (e.g., "Matt Sikora", "admin")
- Institution names (e.g., "UPMC", "Sikora Lab")
- Experiment identifiers
- Sample IDs and aliquot IDs

## Anonymization Process

### Files Created

1. **`tests/scripts/anonymize_csv.py`** - The anonymization script
2. **`tests/data/anonymized_test_data.csv`** - The anonymized dataset for testing
3. **`tests/scripts/test_anonymized_data.py`** - Verification script to ensure proper anonymization
4. **`tests/fixtures/sample_fixtures.json`** - Django fixtures generated from anonymized data

### What Gets Anonymized

#### Cell Lines
- Original: "MDA MB 134VI (MM134)" → Anonymized: "CELL_HBRP"
- Original: "SUM44PE" → Anonymized: "CELL_SDFO"
- Pattern: `CELL_` + random 4-character alphanumeric ID

#### Personal Names
- Original: "Matt Sikora" → Anonymized: "User Researcher"
- Original: "admin" → Anonymized: "Test Admin"
- Pattern: Random combinations of ["Test", "Sample", "Demo", "Anon", "User"] + ["Researcher", "Scientist", "Technician", "Analyst", "Operator"]

#### Institutions and Labs
- Original: "UPMC" → Anonymized: "Test Institution"
- Original: "Sikora Lab" → Anonymized: "Test Lab"
- Original: "Rae Lab" → Anonymized: "Test Lab"

#### IDs and Identifiers
- Freezerworks ID: `TEST_` + random 5-character ID
- Globally Unique Sample ID: `TEST_SAMPLE_` + random 6-character ID
- Globally Unique Aliquot ID: `TEST_ALIQUOT_` + random 6-character ID
- Unique Aliquot ID: `TEST_UA_` + random 6-character ID
- Parent Aliquot ID: `TEST_PARENT_` + random 5-character ID

#### Experiments
- Original: "MJS_0049" → Anonymized: "EXP_VE6P"
- Pattern: `EXP_` + random 4-character alphanumeric ID

#### Sources
- Original: "UPMC/MJS" → Anonymized: "SOURCE_OIG"
- Pattern: `SOURCE_` + random 3-character alphanumeric ID

#### Freezers
- Original: "Sikora LN2 #1" → Anonymized: "FREEZER_FNO"
- Pattern: `FREEZER_` + random 3-character alphanumeric ID

## Usage

### Generating Anonymized Data

```bash
cd tests/scripts
python anonymize_csv.py
```

This will:
1. Read the original `ln2_cane4_export.csv` from the project root
2. Apply anonymization rules
3. Generate `tests/data/anonymized_test_data.csv`

### Verifying Anonymization

```bash
cd tests/scripts
python test_anonymized_data.py
```

This will:
1. Check for any remaining sensitive data patterns
2. Analyze the anonymized data structure
3. Test the conversion process
4. Generate Django fixtures in `tests/fixtures/`

### Using the Test Data

The anonymized data can be used for:
- Development and testing
- CI/CD pipelines
- Documentation examples
- Training and demonstrations

### Converting to Django Fixtures

```bash
cd tests/scripts
python convert_csv.py
```

This will generate `tests/fixtures/sample_fixtures.json` containing Django fixtures that can be loaded into a test database.

### Running All Tests

```bash
python tests/run_tests.py
```

This will run all the above steps in sequence and provide a comprehensive test report.

### Creating Test Superuser

```bash
make create-test-superuser
```

This creates a test superuser with username `admin` and password `admin` for accessing the Django admin interface.

## Data Structure

The anonymized data maintains the same structure as the original:
- 871 rows of sample data
- 67 unique cell lines
- 10 unique experiments
- 14 unique sources
- 16 unique persons
- 1683 Django fixtures generated

## Security Notes

- The original dataset should never be committed to version control
- Only the anonymized data should be used for testing
- The anonymization script uses a fixed random seed (42) for reproducible results
- All sensitive patterns are systematically replaced with generic test identifiers

## Maintenance

If new sensitive patterns are discovered:
1. Add them to the `sensitive_replacements` dictionary in `anonymize_csv.py`
2. Regenerate the anonymized data
3. Run the verification script to ensure proper anonymization

## Files to Include in Version Control

✅ **Include these files:**
- `tests/scripts/anonymize_csv.py`
- `tests/data/anonymized_test_data.csv`
- `tests/scripts/test_anonymized_data.py`
- `tests/scripts/convert_csv.py`
- `tests/scripts/create_test_superuser.py`
- `tests/fixtures/sample_fixtures.json`
- `tests/ANONYMIZATION_README.md`
- `tests/TESTING_TODO.md`

❌ **Do NOT include:**
- `ln2_cane4_export.csv` (original sensitive data)

## Example Usage in Tests

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
