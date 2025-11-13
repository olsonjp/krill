import csv
import json
from datetime import datetime
from collections import defaultdict

def convert_csv_to_fixtures(csv_file):
    fixtures = []
    pk_counter = defaultdict(lambda: 1)
    # Mapping dictionaries to track created objects
    sources = {}
    samples = {}
    storage = {'sites': {}, 'devices': {}, 'shelves': {}, 'racks': {}, 'boxes': {}}
    aliquot_types = {}
    dispositions = {}
    # Read CSV file
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Create Source if not exists
            source_name = row['Source'] or 'Unknown'
            if source_name not in sources:
                sources[source_name] = pk_counter['source']
                fixtures.append({
                    'model': 'sample.source',
                    'pk': sources[source_name],
                    'fields': {
                        'name': source_name,
                        'description': ''
                    }
                })
                pk_counter['source'] += 1
            # Create Sample if not exists
            sample_key = row['Cell Line']
            current_notes = row['Sample Notes'] or ''
            if sample_key not in samples:
                samples[sample_key] = pk_counter['sample']
                fixtures.append({
                    'model': 'sample.sample',
                    'fields': {
                        'name': row['Cell Line'],
                        'experiment': row['Experiment #'] or '',
                        'source': sources[source_name],
                        'notes': current_notes
                    }
                })
                pk_counter['sample'] += 1
            else:
                # Sample exists, check if we need to append notes
                existing_sample = next((fixture for fixture in fixtures if fixture['model'] == 'sample.sample' and fixture['fields']['name'] == sample_key), None)
                if existing_sample and current_notes and current_notes not in existing_sample['fields']['notes']:
                    existing_notes = existing_sample['fields']['notes']
                    if existing_notes:
                        existing_sample['fields']['notes'] = existing_notes + '\n' + current_notes
                    else:
                        existing_sample['fields']['notes'] = current_notes
            # Create Storage hierarchy
            # Use Site column if provided, otherwise default to "Default Site"
            site_name = row.get('Site', '').strip() or 'Default Site'
            freezer_name = row['Freezer Name']
            shelf_name = "Shelf 1"
            rack_name = row['Position 1']
            box_name = row['Position 2']

            if site_name not in storage['sites']:
                storage['sites'][site_name] = pk_counter['site']
                fixtures.append({
                    'model': 'storage.site',
                    'pk': storage['sites'][site_name],
                    'fields': {'name': site_name}
                })
            if freezer_name:
                # Create Device if not exists
                if freezer_name not in storage['devices']:
                    storage['devices'][freezer_name] = pk_counter['device']
                    fixtures.append({
                        'model': 'storage.device',
                        'pk': storage['devices'][freezer_name],
                        'fields': {
                            'name': freezer_name,
                            'description': '',
                            'site': storage['sites'][site_name]
                        }
                    })
                    pk_counter['device'] += 1
            if shelf_name and rack_name and box_name:
                # Create Shelf if not exists
                if shelf_name not in storage['shelves']:
                    storage['shelves'][shelf_name] = pk_counter['shelf']
                    fixtures.append({
                        'model': 'storage.shelf',
                        'pk': storage['shelves'][shelf_name],
                        'fields': {
                            'name': shelf_name,
                            'description': '',
                            'device': storage['devices'][freezer_name]
                        }
                    })
                    pk_counter['shelf'] += 1
                if rack_name:
                    # Create Rack if not exists
                    if rack_name not in storage['racks']:
                        storage['racks'][rack_name] = pk_counter['rack']
                        fixtures.append({
                            'model': 'storage.rack',
                            'pk': storage['racks'][rack_name],
                            'fields': {'name': rack_name,
                            'description': '',
                            'shelf': storage['shelves'][shelf_name]
                        }
                        })
                        pk_counter['rack'] += 1
                    # Create Box if not exists
                    box_key = f"{shelf_name}_{rack_name}_{box_name}"
                    if box_key not in storage['boxes']:
                        storage['boxes'][box_key] = pk_counter['box']
                        fixtures.append({
                            'model': 'storage.box',
                            'pk': storage['boxes'][box_key],
                            'fields': {
                            'name': box_name,
                            'description': '',
                            'rack': storage['racks'][rack_name],
                            'rows': 10,
                            'columns': 10
                        }
                    })
                    pk_counter['box'] += 1
            # Create AliquotType if not exists
            aliquot_type = row['Aliquot Type'] or 'Unknown'
            if aliquot_type not in aliquot_types:
                aliquot_types[aliquot_type] = pk_counter['aliquot_type']
                fixtures.append({
                    'model': 'sample.aliquottype',
                    'pk': aliquot_types[aliquot_type],
                    'fields': {
                        'name': aliquot_type,
                        'description': ''
                    }
                })
                pk_counter['aliquot_type'] += 1
            # Map disposition
            disposition_map = {
                'In Storage': 'stored',
                'Used': 'exhausted',
                'Checked Out': 'in_use'
            }
            disposition = row['Disposition'] or 'In Storage'
            disp_type = disposition_map.get(disposition, 'stored')
            if disposition not in dispositions:
                dispositions[disposition] = pk_counter['disposition']
                fixtures.append({
                    'model': 'sample.aliquotdisposition',
                    'pk': dispositions[disposition],
                    'fields': {
                        'name': disposition,
                        'dispositionType': disp_type,
                        'description': ''
                    }
                })
                pk_counter['disposition'] += 1
            # Create Aliquot
            aliquot_pk = pk_counter['aliquot']
            fixtures.append({
                'model': 'sample.aliquot',
                'pk': aliquot_pk,
                'fields': {
                    'parent': None,  # Could be mapped if needed
                    'sample': samples[sample_key],
                    'quantity': int(float(row['Current Amount'] or 0)),
                    'aliquotType': aliquot_types[aliquot_type],
                    'passage': row['Aliquot/SubA Passage#'] or '0',
                    'experiment': row['Experiment #'] or '',
                    'notes': row['Aliquot Notes'] or ''
                }
            })
            pk_counter['aliquot'] += 1
            # Create AliquotTube for this aliquot
            quantity = int(float(row['Current Amount'] or 0))
            if quantity > 0:
                for tube_num in range(1, quantity + 1):
                    # Create tube
                    tube_pk = pk_counter['tube']
                    fixtures.append({
                        'model': 'sample.aliquottube',
                        'pk': tube_pk,
                        'fields': {
                            'aliquot': aliquot_pk,
                            'tube_number': tube_num,
                            'disposition': dispositions[disposition]
                        }
                    })
                    pk_counter['tube'] += 1

                    # Create AliquotLocation if box exists and this is the first tube
                    if tube_num == 1 and box_key in storage['boxes'] and row['Position 3'] and row['Position 4']:
                        fixtures.append({
                            'model': 'sample.aliquotlocation',
                            'pk': pk_counter['location'],
                            'fields': {
                                'aliquot': aliquot_pk,
                                'tube_number': tube_num,
                                'box': storage['boxes'][box_key],
                                'row': int(row['Position 3']),
                                'column': int(row['Position 4'])
                            }
                        })
                        pk_counter['location'] += 1
    # Write fixtures to file
    with open('../fixtures/sample_fixtures.json', 'w') as f:
        json.dump(fixtures, f, indent=2)

# Usage
# Note: This script now uses the anonymized test data by default
# The original sensitive data should not be used for testing
convert_csv_to_fixtures('../data/anonymized_test_data.csv')
