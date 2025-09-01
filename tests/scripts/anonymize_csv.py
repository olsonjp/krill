import csv
import random
import string
from datetime import datetime, timedelta

def generate_random_id(prefix="", length=6):
    """Generate a random alphanumeric ID"""
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choice(chars) for _ in range(length))

def generate_random_name():
    """Generate a random name for anonymization"""
    first_names = ["Test", "Sample", "Demo", "Anon", "User"]
    last_names = ["Researcher", "Scientist", "Technician", "Analyst", "Operator"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def anonymize_csv(input_file, output_file):
    """Anonymize the CSV file while preserving data structure"""
    
    # Mapping dictionaries to maintain consistency
    cell_line_mapping = {}
    experiment_mapping = {}
    source_mapping = {}
    person_mapping = {}
    freezer_mapping = {}
    
    # Read the original CSV and create anonymized version
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile, delimiter=';')
        fieldnames = reader.fieldnames
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        
        for row in reader:
            anonymized_row = {}
            for field in fieldnames:
                anonymized_row[field] = row.get(field, '')
            
            # Anonymize Cell Line
            original_cell_line = row['Cell Line']
            if original_cell_line not in cell_line_mapping:
                cell_line_mapping[original_cell_line] = f"CELL_{generate_random_id('', 4)}"
            anonymized_row['Cell Line'] = cell_line_mapping[original_cell_line]
            
            # Anonymize Experiment #
            original_experiment = row['Experiment #']
            if original_experiment and original_experiment not in experiment_mapping:
                experiment_mapping[original_experiment] = f"EXP_{generate_random_id('', 4)}"
            if original_experiment:
                anonymized_row['Experiment #'] = experiment_mapping[original_experiment]
            
            # Anonymize Source
            original_source = row['Source']
            if original_source and original_source not in source_mapping:
                source_mapping[original_source] = f"SOURCE_{generate_random_id('', 3)}"
            if original_source:
                anonymized_row['Source'] = source_mapping[original_source]
            
            # Anonymize personal names
            for field in ['Created By Name', 'Lab Member', 'Sample Modified By', 
                         'Aliquot Modified By', 'Lab Member (sub-aliquots)', 
                         'Transaction User Name']:
                if row[field] and row[field] not in person_mapping:
                    person_mapping[row[field]] = generate_random_name()
                if row[field]:
                    anonymized_row[field] = person_mapping[row[field]]
            
            # Anonymize Freezer Name
            original_freezer = row['Freezer Name']
            if original_freezer and original_freezer not in freezer_mapping:
                freezer_mapping[original_freezer] = f"FREEZER_{generate_random_id('', 3)}"
            if original_freezer:
                anonymized_row['Freezer Name'] = freezer_mapping[original_freezer]
            
            # Anonymize IDs while preserving format
            if row['Freezerworks ID']:
                anonymized_row['Freezerworks ID'] = f"TEST_{generate_random_id('', 5)}"
            
            if row['Globally Unique Sample ID']:
                anonymized_row['Globally Unique Sample ID'] = f"TEST_SAMPLE_{generate_random_id('', 6)}"
            
            if row['Globally Unique Aliquot ID']:
                anonymized_row['Globally Unique Aliquot ID'] = f"TEST_ALIQUOT_{generate_random_id('', 6)}"
            
            if row['Unique Aliquot ID']:
                anonymized_row['Unique Aliquot ID'] = f"TEST_UA_{generate_random_id('', 6)}"
            
            if row['Parent Aliquot ID']:
                anonymized_row['Parent Aliquot ID'] = f"TEST_PARENT_{generate_random_id('', 5)}"
            
            # Anonymize Subject ID
            if row['Subject ID']:
                anonymized_row['Subject ID'] = f"SUBJECT_{generate_random_id('', 4)}"
            
            # Anonymize notes while preserving structure
            for field in ['Notes', 'Sample Notes', 'Aliquot Notes', 'Transaction Notes']:
                if row[field]:
                    # Replace specific names/identifiers in notes with generic text
                    note = row[field]
                    for original_name, anonymized_name in person_mapping.items():
                        note = note.replace(original_name, anonymized_name)
                    for original_cell, anonymized_cell in cell_line_mapping.items():
                        note = note.replace(original_cell, anonymized_cell)
                    
                    # Replace additional sensitive patterns
                    sensitive_replacements = {
                        'Sikora': 'Test Lab',
                        'UPMC': 'Test Institution',
                        'Pittsburgh': 'Test City',
                        'Rae Lab': 'Test Lab',
                        'Rae Laboratory': 'Test Laboratory',
                        'Ethier Lab': 'Test Lab',
                        'Beth Knapick': 'Test Researcher',
                        'Jennifer Xavier': 'Test Researcher',
                        'MTS': 'Test Technician',
                        'EKB': 'Test Analyst',
                        'JS': 'Test Scientist',
                        'DMR': 'Test Operator',
                        'RF': 'Test Researcher',
                        'Matt': 'Test User',
                        'admin': 'Test Admin'
                    }
                    
                    for sensitive, replacement in sensitive_replacements.items():
                        note = note.replace(sensitive, replacement)
                    
                    anonymized_row[field] = note
            
            writer.writerow(anonymized_row)
    
    print(f"Anonymized data written to {output_file}")
    print(f"Generated {len(cell_line_mapping)} unique cell lines")
    print(f"Generated {len(experiment_mapping)} unique experiments")
    print(f"Generated {len(source_mapping)} unique sources")
    print(f"Generated {len(person_mapping)} unique persons")

if __name__ == "__main__":
    # Set random seed for reproducible anonymization
    random.seed(42)
    
    input_file = "../../ln2_cane4_export.csv"
    output_file = "../data/anonymized_test_data.csv"
    
    anonymize_csv(input_file, output_file)
