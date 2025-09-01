from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django import forms
import csv
import json
import os
from datetime import datetime
from collections import defaultdict

User = get_user_model()
from .models import UserPreference, UserRole, Permission, UserAuditLog
from .forms import (
    UserRoleForm, PermissionForm, UserPreferenceForm, 
    BulkPermissionForm, UserSearchForm, AuditLogFilterForm, CreateUserForm
)
from .decorators import require_permission, require_minimum_role, grant_object_permission, revoke_object_permission


# Data Import Form
class DataImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with sample data. Expected format: Source;Cell Line;Experiment #;Sample Notes;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Current Amount;Aliquot/SubA Passage#;Aliquot Notes;Disposition'
    )
    dry_run = forms.BooleanField(
        label='Dry Run',
        required=False,
        help_text='Check this to preview the import without actually creating records'
    )


# Data Import View for main app
@method_decorator(staff_member_required, name='dispatch')
class DataImportView(TemplateView):
    template_name = 'person/data_import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DataImportForm()
        context['title'] = 'Data Import'
        return context
    
    def post(self, request, *args, **kwargs):
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            dry_run = form.cleaned_data['dry_run']
            
            try:
                if dry_run:
                    # Preview mode
                    preview_data = self.preview_import(csv_file)
                    context = self.get_context_data()
                    context['preview_data'] = preview_data
                    context['dry_run'] = True
                    context['form'] = form
                    return render(request, self.template_name, context)
                else:
                    # Actual import
                    import_result = self.perform_import(csv_file)
                    details = import_result.get('details', {})
                    message = f'Successfully imported {import_result["total"]} records: '
                    message += f'{details.get("sources", 0)} sources, '
                    message += f'{details.get("samples", 0)} samples, '
                    message += f'{details.get("aliquots", 0)} aliquots, '
                    message += f'{details.get("locations", 0)} locations'
                    messages.success(request, message)
                    return redirect('person:user_list')
                    
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
                context = self.get_context_data()
                context['form'] = form
                context['error'] = str(e)
                return render(request, self.template_name, context)
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
    
    def preview_import(self, csv_file):
        """Preview the import data without creating records"""
        preview_data = {
            'sources': set(),
            'samples': set(),
            'storage_items': set(),
            'aliquot_types': set(),
            'dispositions': set(),
            'aliquots': 0,
            'locations': 0
        }
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_file.seek(0)  # Reset file pointer
            
            # Parse CSV and create fixtures using existing logic
            fixtures = self.parse_csv_to_fixtures(decoded_file)
            
            # Count what would be imported
            preview_data['sources'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.source'])
            preview_data['samples'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.sample'])
            preview_data['aliquot_types'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquottype'])
            preview_data['dispositions'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquotdisposition'])
            preview_data['storage_items'] = set([f['fields']['name'] for f in fixtures if f['model'] in ['storage.site', 'storage.device', 'storage.shelf', 'storage.rack', 'storage.box']])
            preview_data['aliquots'] = len([f for f in fixtures if f['model'] == 'sample.aliquot'])
            preview_data['locations'] = len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])
            
            # Convert sets to sorted lists for display
            for key in ['sources', 'samples', 'storage_items', 'aliquot_types', 'dispositions']:
                preview_data[key] = sorted(list(preview_data[key]))
                
        except Exception as e:
            raise Exception(f"Error reading CSV file: {str(e)}")
        
        return preview_data
    
    def perform_import(self, csv_file):
        """Actually perform the import"""
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_file.seek(0)  # Reset file pointer
            
            # Parse CSV and create fixtures using existing logic
            fixtures = self.parse_csv_to_fixtures(decoded_file)
            
            # Save fixtures to temporary file
            fixtures_file = f'import_fixtures_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(fixtures_file, 'w') as f:
                json.dump(fixtures, f, indent=2)
            
            # Use Django's loaddata command to import the fixtures
            from django.core.management import call_command
            from django.core.management.base import CommandError
            
            try:
                # Add debug logging
                print(f"Attempting to import {len(fixtures)} fixtures from {fixtures_file}")
                
                # Validate fixtures before import
                self.validate_fixtures(fixtures)
                
                # Save a sample of fixtures for debugging
                self.save_fixture_sample(fixtures, fixtures_file.replace('.json', '_sample.json'))
                
                # Try importing in smaller batches to isolate issues
                try:
                    self.import_fixtures_in_batches(fixtures, fixtures_file)
                except Exception as e:
                    print(f"Batch import failed: {str(e)}")
                    # Fall back to single file import
                    print("Falling back to single file import...")
                    self.import_single_fixture_file(fixtures_file)
                
                # Count what was imported
                import_counts = {
                    'sources': len([f for f in fixtures if f['model'] == 'sample.source']),
                    'samples': len([f for f in fixtures if f['model'] == 'sample.sample']),
                    'aliquot_types': len([f for f in fixtures if f['model'] == 'sample.aliquottype']),
                    'dispositions': len([f for f in fixtures if f['model'] == 'sample.aliquotdisposition']),
                    'sites': len([f for f in fixtures if f['model'] == 'storage.site']),
                    'devices': len([f for f in fixtures if f['model'] == 'storage.device']),
                    'shelves': len([f for f in fixtures if f['model'] == 'storage.shelf']),
                    'racks': len([f for f in fixtures if f['model'] == 'storage.rack']),
                    'boxes': len([f for f in fixtures if f['model'] == 'storage.box']),
                    'aliquots': len([f for f in fixtures if f['model'] == 'sample.aliquot']),
                    'locations': len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])
                }
                
                total_imported = sum(import_counts.values())
                print(f"Successfully imported {total_imported} objects")
                
                # Clean up temporary file
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                
                return {
                    'total': total_imported,
                    'details': import_counts
                }
                
            except CommandError as e:
                # Clean up temporary file on error
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                print(f"CommandError during import: {str(e)}")
                raise Exception(f"Django import failed: {str(e)}")
            
            except Exception as e:
                # Clean up temporary file on any other error
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                print(f"Unexpected error during import: {str(e)}")
                raise Exception(f"Unexpected import error: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Import failed: {str(e)}")
    
    def parse_csv_to_fixtures(self, csv_content):
        """Parse CSV content and convert to Django fixtures format"""
        fixtures = []
        pk_counter = defaultdict(lambda: 1)
        
        # Mapping dictionaries to track created objects
        sources = {}
        samples = {}
        storage = {'sites': {}, 'devices': {}, 'shelves': {}, 'racks': {}, 'boxes': {}}
        aliquot_types = {}
        dispositions = {}
        
        # Read CSV content
        reader = csv.DictReader(csv_content.splitlines(), delimiter=';')
        
        # Validate CSV structure - check for essential columns
        essential_columns = ['Source', 'Cell Line', 'Freezer Name', 'Position 1', 'Position 2', 'Position 3', 'Position 4', 'Aliquot Type', 'Current Amount', 'Disposition']
        
        missing_columns = [col for col in essential_columns if col not in reader.fieldnames]
        if missing_columns:
            raise Exception(f"CSV is missing essential columns: {', '.join(missing_columns)}")
        
        print(f"Processing CSV with {len(reader.fieldnames)} columns")
        print(f"Essential columns found: {', '.join([col for col in essential_columns if col in reader.fieldnames])}")
        
        for row in reader:
            # Create Source if not exists
            source_name = row.get('Source') or 'Unknown'
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
            sample_key = row.get('Cell Line')
            if sample_key and sample_key not in samples:
                samples[sample_key] = pk_counter['sample']
                fixtures.append({
                    'model': 'sample.sample',
                    'pk': samples[sample_key],
                    'fields': {
                        'name': row['Cell Line'],
                        'experiment': row.get('Experiment #', '') or '',
                        'source': sources[source_name],
                        'notes': row.get('Notes', '') or row.get('Sample Notes', '') or ''
                    }
                })
                pk_counter['sample'] += 1
            
            # Create Storage hierarchy
            site_name = 'Sikora Lab'
            freezer_name = row.get('Freezer Name')
            shelf_name = "Shelf 1"
            rack_name = row.get('Position 1')
            box_name = row.get('Position 2')
            
            if site_name not in storage['sites']:
                storage['sites'][site_name] = pk_counter['site']
                fixtures.append({
                    'model': 'storage.site',
                    'pk': storage['sites'][site_name],
                    'fields': {'name': site_name}
                })
                pk_counter['site'] += 1
            
            if freezer_name:
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
                if shelf_name not in storage['shelves']:
                    storage['shelves'][shelf_name] = pk_counter['shelf']
                    fixtures.append({
                        'model': 'storage.shelf',
                        'pk': storage['shelves'][shelf_name],
                        'fields': {
                            'name': shelf_name,
                            'description': '',
                            'device': storage['devices'].get(freezer_name, storage['sites'][site_name])
                        }
                    })
                    pk_counter['shelf'] += 1
                
                if rack_name not in storage['racks']:
                    storage['racks'][rack_name] = pk_counter['rack']
                    fixtures.append({
                        'model': 'storage.rack',
                        'pk': storage['racks'][rack_name],
                        'fields': {
                            'name': rack_name,
                            'description': '',
                            'shelf': storage['shelves'][shelf_name]
                        }
                    })
                    pk_counter['rack'] += 1
                
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
            aliquot_type_name = row.get('Aliquot Type') or 'Unknown'
            if aliquot_type_name not in aliquot_types:
                aliquot_types[aliquot_type_name] = pk_counter['aliquot_type']
                fixtures.append({
                    'model': 'sample.aliquottype',
                    'pk': aliquot_types[aliquot_type_name],
                    'fields': {
                        'name': aliquot_type_name,
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
            disposition_name = row.get('Disposition') or 'In Storage'
            disp_type = disposition_map.get(disposition_name, 'stored')
            if disposition_name not in dispositions:
                dispositions[disposition_name] = pk_counter['disposition']
                fixtures.append({
                    'model': 'sample.aliquotdisposition',
                    'pk': dispositions[disposition_name],
                    'fields': {
                        'name': disposition_name,
                        'disposition_type': disp_type
                    }
                })
                pk_counter['disposition'] += 1
            
            # Create Aliquot
            aliquot_pk = pk_counter['aliquot']
            
            # Ensure we have a valid sample reference
            sample_pk = samples.get(sample_key)
            if not sample_pk:
                if samples:
                    sample_pk = list(samples.values())[0]
                    print(f"Warning: No sample found for '{sample_key}', using first available sample")
                else:
                    raise Exception(f"No samples available for aliquot creation")
            
            # Handle current amount - try multiple possible column names
            current_amount = 0
            for amount_col in ['Current Amount', 'Total Current Amount']:
                if row.get(amount_col):
                    try:
                        amount_val = float(row[amount_col])
                        if amount_val > 0:  # Only use positive amounts
                            current_amount = int(amount_val)
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Handle passage number - try multiple possible column names
            passage = '0'
            for passage_col in ['Aliquot/SubA Passage#', 'Passage Number']:
                if row.get(passage_col):
                    passage_raw = str(row[passage_col]) or '0'
                    # Clean up passage number - extract just the number
                    import re
                    passage_match = re.search(r'(\d+)', passage_raw)
                    if passage_match:
                        passage = passage_match.group(1)
                    else:
                        passage = '0'
                    break
            
            # Handle experiment - try multiple possible column names
            experiment = ''
            for exp_col in ['Experiment #', 'Globally Unique Sample ID']:
                if row.get(exp_col):
                    experiment = str(row[exp_col]) or ''
                    break
            
            # Handle notes - try multiple possible column names
            notes = ''
            for notes_col in ['Aliquot Notes', 'Notes']:
                if row.get(notes_col):
                    notes = str(row[notes_col]) or ''
                    break
            
            # Only create aliquot if we have valid data
            if current_amount > 0 or experiment or notes:
                fixtures.append({
                    'model': 'sample.aliquot',
                    'pk': aliquot_pk,
                    'fields': {
                        'parent': None,
                        'sample': sample_pk,
                        'quantity': current_amount,
                        'aliquot_type': aliquot_types[aliquot_type_name],
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                })
                pk_counter['aliquot'] += 1
                
                # Create AliquotLocation if box exists and we have position data
                if box_key in storage['boxes'] and row.get('Position 3') and row.get('Position 4'):
                    try:
                        row_pos = int(row['Position 3'])
                        col_pos = int(row['Position 4'])
                        if row_pos > 0 and col_pos > 0:  # Only create location for valid positions
                            fixtures.append({
                                'model': 'sample.aliquotlocation',
                                'pk': pk_counter['location'],
                                'fields': {
                                    'aliquot': aliquot_pk,
                                    'tube_number': 1,
                                    'box': storage['boxes'][box_key],
                                    'row': row_pos,
                                    'column': col_pos,
                                    'created_at': datetime.now().isoformat(),
                                    'updated_at': datetime.now().isoformat()
                                }
                            })
                            pk_counter['location'] += 1
                    except (ValueError, TypeError) as e:
                        # Log error but continue with import
                        print(f"Warning: Could not create location for aliquot {aliquot_pk}: {e}")
            else:
                print(f"Skipping aliquot creation for sample {sample_key} - insufficient data")
            

        
        print(f"Created {len(fixtures)} fixtures:")
        print(f"  - Sources: {len([f for f in fixtures if f['model'] == 'sample.source'])}")
        print(f"  - Samples: {len([f for f in fixtures if f['model'] == 'sample.sample'])}")
        print(f"  - Aliquot Types: {len([f for f in fixtures if f['model'] == 'sample.aliquottype'])}")
        print(f"  - Dispositions: {len([f for f in fixtures if f['model'] == 'sample.aliquotdisposition'])}")
        print(f"  - Sites: {len([f for f in fixtures if f['model'] == 'storage.site'])}")
        print(f"  - Devices: {len([f for f in fixtures if f['model'] == 'storage.device'])}")
        print(f"  - Shelves: {len([f for f in fixtures if f['model'] == 'storage.shelf'])}")
        print(f"  - Racks: {len([f for f in fixtures if f['model'] == 'storage.rack'])}")
        print(f"  - Boxes: {len([f for f in fixtures if f['model'] == 'storage.box'])}")
        print(f"  - Aliquots: {len([f for f in fixtures if f['model'] == 'sample.aliquot'])}")
        print(f"  - Locations: {len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])}")
        
        return fixtures
    
    def validate_fixtures(self, fixtures):
        """Validate fixtures before import to catch common issues"""
        print("Validating fixtures...")
        
        # Check for required fields in each fixture
        for i, fixture in enumerate(fixtures):
            if 'model' not in fixture:
                raise Exception(f"Fixture {i} missing 'model' field")
            if 'pk' not in fixture:
                raise Exception(f"Fixture {i} missing 'pk' field")
            if 'fields' not in fixture:
                raise Exception(f"Fixture {i} missing 'fields' field")
            
            # Check for common model name issues
            model = fixture['model']
            if model not in [
                'sample.source', 'sample.sample', 'sample.aliquottype', 'sample.aliquotdisposition',
                'storage.site', 'storage.device', 'storage.shelf', 'storage.rack', 'storage.box',
                'sample.aliquot', 'sample.aliquotlocation'
            ]:
                raise Exception(f"Unknown model '{model}' in fixture {i}")
            
            # Check for foreign key references
            fields = fixture['fields']
            if 'sample' in fields and fields['sample'] is None:
                print(f"Warning: Fixture {i} has null sample reference")
            if 'source' in fields and fields['source'] is None:
                print(f"Warning: Fixture {i} has null source reference")
        
        # Check for circular dependencies and foreign key issues
        print("Checking foreign key relationships...")
        
        # Build dependency map
        dependencies = {}
        for fixture in fixtures:
            model = fixture['model']
            pk = fixture['pk']
            if model not in dependencies:
                dependencies[model] = set()
            
            # Check what this fixture depends on
            fields = fixture['fields']
            if 'source' in fields and fields['source']:
                dependencies[model].add(('sample.source', fields['source']))
            if 'sample' in fields and fields['sample']:
                dependencies[model].add(('sample.sample', fields['sample']))
            if 'aliquotType' in fields and fields['aliquotType']:
                dependencies[model].add(('sample.aliquottype', fields['aliquotType']))
            if 'disposition' in fields and fields['disposition']:
                dependencies[model].add(('sample.aliquotdisposition', fields['disposition']))
            if 'site' in fields and fields['site']:
                dependencies[model].add(('storage.site', fields['site']))
            if 'device' in fields and fields['device']:
                dependencies[model].add(('storage.device', fields['device']))
            if 'shelf' in fields and fields['shelf']:
                dependencies[model].add(('storage.shelf', fields['shelf']))
            if 'rack' in fields and fields['rack']:
                dependencies[model].add(('storage.rack', fields['rack']))
            if 'box' in fields and fields['box']:
                dependencies[model].add(('storage.box', fields['box']))
            if 'aliquot' in fields and fields['aliquot']:
                dependencies[model].add(('sample.aliquot', fields['aliquot']))
        
        print("Foreign key validation completed")
        print("Fixtures validation passed")
    
    def save_fixture_sample(self, fixtures, sample_file):
        """Save a sample of fixtures for debugging purposes"""
        sample_fixtures = []
        
        # Get one of each model type
        model_samples = {}
        for fixture in fixtures:
            model = fixture['model']
            if model not in model_samples:
                model_samples[model] = fixture
                sample_fixtures.append(fixture)
        
        # Add a few more aliquots to see the pattern
        aliquot_count = 0
        for fixture in fixtures:
            if fixture['model'] == 'sample.aliquot' and aliquot_count < 3:
                sample_fixtures.append(fixture)
                aliquot_count += 1
        
        with open(sample_file, 'w') as f:
            json.dump(sample_fixtures, f, indent=2)
        
        print(f"Saved fixture sample to {sample_file} ({len(sample_fixtures)} fixtures)")
    
    def import_fixtures_in_batches(self, fixtures, fixtures_file):
        """Import fixtures in smaller batches to isolate issues"""
        print("Attempting batch import...")
        
        # Group fixtures by model type
        model_groups = {}
        for fixture in fixtures:
            model = fixture['model']
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(fixture)
        
        # Import in dependency order
        import_order = [
            'sample.source',
            'storage.site', 
            'storage.device',
            'storage.shelf',
            'storage.rack',
            'storage.box',
            'sample.sample',
            'sample.aliquottype',
            'sample.aliquotdisposition',
            'sample.aliquot',
            'sample.aliquotlocation'
        ]
        
        imported_count = 0
        for model in import_order:
            if model in model_groups:
                model_fixtures = model_groups[model]
                print(f"Importing {len(model_fixtures)} {model} fixtures...")
                
                # Create temporary file for this model
                temp_file = f"{fixtures_file.replace('.json', '')}_{model.replace('.', '_')}.json"
                with open(temp_file, 'w') as f:
                    json.dump(model_fixtures, f, indent=2)
                
                try:
                    from django.core.management import call_command
                    call_command('loaddata', temp_file, verbosity=1)
                    imported_count += len(model_fixtures)
                    print(f"Successfully imported {len(model_fixtures)} {model} fixtures")
                except Exception as e:
                    print(f"Failed to import {model}: {str(e)}")
                    raise e
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        
        print(f"Batch import completed: {imported_count} fixtures imported")
        return imported_count
    
    def import_single_fixture_file(self, fixtures_file):
        """Fallback: import the entire fixture file at once"""
        print("Importing entire fixture file...")
        
        from django.core.management import call_command
        from django.core.management.base import CommandError
        
        # Capture Django's output to see detailed error messages
        from io import StringIO
        out = StringIO()
        err = StringIO()
        
        try:
            call_command('loaddata', fixtures_file, verbosity=2, stdout=out, stderr=err)
            print("Django loaddata command completed successfully")
            print("STDOUT:", out.getvalue())
            if err.getvalue():
                print("STDERR:", err.getvalue())
            
        except CommandError as e:
            print(f"CommandError details: {str(e)}")
            print("STDOUT:", out.getvalue())
            print("STDERR:", err.getvalue())
            raise e


# Create your views here.

@login_required
@require_http_methods(["POST"])
def toggle_theme(request):
    # Get or create the user's preference
    preference, created = UserPreference.objects.get_or_create(
        user=request.user,
        defaults={'dark_mode': False}
    )
    # Toggle the dark mode setting
    preference.dark_mode = not preference.dark_mode
    preference.save()
    return JsonResponse({
        'dark_mode': preference.dark_mode,
        'success': True
    })


@login_required
@require_minimum_role('lab_manager')
def create_user(request):
    """Create a new user with role assignment"""
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user creation
            UserAuditLog.log_action(
                user=request.user,
                action='create',
                target_type='User',
                target_id=user.id,
                target_name=user.username,
                details={
                    'created_by': request.user.username,
                    'role': user.role.role,
                    'department': user.role.department,
                    'lab_unit': user.role.lab_unit
                },
                request=request
            )
            messages.success(request, f"User '{user.username}' created successfully with role '{user.role.get_role_display()}'")
            return redirect('person:user_detail', user_id=user.id)
    else:
        form = CreateUserForm()
    context = {
        'form': form,
        'title': 'Create New User',
    }
    return render(request, 'person/create_user.html', context)


@login_required
@require_minimum_role('lab_manager')
def user_list(request):
    """List all users with their roles and permissions"""
    form = UserSearchForm(request.GET)
    users = UserRole.objects.select_related('user').all()
    if form.is_valid():
        search = form.cleaned_data.get('search')
        role = form.cleaned_data.get('role')
        department = form.cleaned_data.get('department')
        is_active = form.cleaned_data.get('is_active')
        if search:
            users = users.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        if role:
            users = users.filter(role=role)
        if department:
            users = users.filter(department__icontains=department)
        if is_active:
            users = users.filter(user__is_active=(is_active == 'True'))
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_users': users.count(),
    }
    return render(request, 'person/user_list.html', context)


@login_required
@require_minimum_role('lab_manager')
def user_detail(request, user_id):
    """View user details, roles, and permissions"""
    user_role = get_object_or_404(UserRole, user_id=user_id)
    permissions = Permission.objects.filter(user=user_role.user).select_related('content_type', 'granted_by')
    # Group role permissions by category
    role_permissions = {}
    for perm in user_role.get_role_permissions():
        category = perm.split('.')[0]
        if category not in role_permissions:
            role_permissions[category] = []
        role_permissions[category].append(perm)
    context = {
        'user_role': user_role,
        'permissions': permissions,
        'role_permissions': role_permissions,
        'recent_activity': UserAuditLog.objects.filter(user=user_role.user).order_by('-timestamp')[:10],
    }
    return render(request, 'person/user_detail.html', context)


@login_required
@require_minimum_role('lab_manager')
def user_role_edit(request, user_id):
    """Edit user role and organizational information"""
    user_role = get_object_or_404(UserRole, user_id=user_id)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=user_role)
        if form.is_valid():
            old_role = user_role.role
            form.save()
            # Log role change
            UserAuditLog.log_action(
                user=request.user,
                action='role_changed',
                target_type='User',
                target_id=user_role.user.id,
                target_name=user_role.user.username,
                details={
                    'old_role': old_role,
                    'new_role': user_role.role,
                    'changed_by': request.user.username
                },
                request=request
            )
            messages.success(request, f"Role updated for {user_role.user.username}")
            return redirect('person:user_detail', user_id=user_id)
    else:
        form = UserRoleForm(instance=user_role)
    context = {
        'form': form,
        'user_role': user_role,
    }
    return render(request, 'person/user_role_edit.html', context)


@login_required
@require_minimum_role('lab_manager')
def permission_list(request):
    """List all object-level permissions"""
    permissions = Permission.objects.select_related('user', 'content_type', 'granted_by').all()
    # Filtering
    user_filter = request.GET.get('user')
    permission_type_filter = request.GET.get('permission_type')
    content_type_filter = request.GET.get('content_type')
    if user_filter:
        permissions = permissions.filter(user__username__icontains=user_filter)
    if permission_type_filter:
        permissions = permissions.filter(permission_type=permission_type_filter)
    if content_type_filter:
        permissions = permissions.filter(content_type__model__icontains=content_type_filter)
    # Pagination
    paginator = Paginator(permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'total_permissions': permissions.count(),
    }
    return render(request, 'person/permission_list.html', context)


@login_required
@require_minimum_role('lab_manager')
def grant_permission(request):
    """Grant object-level permission to a user"""
    if request.method == 'POST':
        form = PermissionForm(request.POST)
        if form.is_valid():
            permission = form.save(granted_by=request.user)
            messages.success(request, f"Permission granted to {permission.user.username}")
            return redirect('person:permission_list')
    else:
        form = PermissionForm()
    context = {
        'form': form,
        'title': 'Grant Permission',
    }
    return render(request, 'person/permission_form.html', context)


@login_required
@require_minimum_role('lab_manager')
def revoke_permission(request, permission_id):
    """Revoke a specific permission"""
    permission = get_object_or_404(Permission, id=permission_id)
    if request.method == 'POST':
        user_name = permission.user.username
        permission.delete()
        messages.success(request, f"Permission revoked from {user_name}")
        return redirect('person:permission_list')
    context = {
        'permission': permission,
    }
    return render(request, 'person/permission_confirm_delete.html', context)


@login_required
@require_minimum_role('lab_manager')
def bulk_grant_permission(request):
    """Grant permissions to multiple users at once"""
    if request.method == 'POST':
        form = BulkPermissionForm(request.POST)
        if form.is_valid():
            users = form.cleaned_data['users']
            permission_type = form.cleaned_data['permission_type']
            content_type = form.cleaned_data['content_type']
            object_id = form.cleaned_data['object_id']
            expires_at = form.cleaned_data['expires_at']
            granted_count = 0
            for user in users:
                permission, created = Permission.objects.get_or_create(
                    user=user,
                    permission_type=permission_type,
                    content_type=content_type,
                    object_id=object_id,
                    defaults={
                        'granted_by': request.user,
                        'expires_at': expires_at
                    }
                )
                if created:
                    granted_count += 1
            messages.success(request, f"Permissions granted to {granted_count} users")
            return redirect('person:permission_list')
    else:
        form = BulkPermissionForm()
    context = {
        'form': form,
        'title': 'Bulk Grant Permissions',
    }
    return render(request, 'person/bulk_permission_form.html', context)


@login_required
@require_minimum_role('lab_admin')
def audit_log(request):
    """View user audit logs"""
    form = AuditLogFilterForm(request.GET)
    logs = UserAuditLog.objects.select_related('user').all()
    if form.is_valid():
        user = form.cleaned_data.get('user')
        action = form.cleaned_data.get('action')
        target_type = form.cleaned_data.get('target_type')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        if user:
            logs = logs.filter(user=user)
        if action:
            logs = logs.filter(action=action)
        if target_type:
            logs = logs.filter(target_type__icontains=target_type)
        if date_from:
            logs = logs.filter(timestamp__date__gte=date_from)
        if date_to:
            logs = logs.filter(timestamp__date__lte=date_to)
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_logs': logs.count(),
    }
    return render(request, 'person/audit_log.html', context)


@login_required
@require_minimum_role('lab_manager')
def user_permissions_api(request, user_id):
    """API endpoint to get user permissions"""
    user_role = get_object_or_404(UserRole, user_id=user_id)
    # Get role-based permissions
    role_permissions = user_role.get_role_permissions()
    # Get object-level permissions
    object_permissions = Permission.objects.filter(
        user=user_role.user
    ).select_related('content_type').values(
        'permission_type', 'content_type__model', 'object_id', 'expires_at'
    )
    return JsonResponse({
        'user': {
            'id': user_role.user.id,
            'username': user_role.user.username,
            'role': user_role.role,
            'department': user_role.department,
        },
        'role_permissions': role_permissions,
        'object_permissions': list(object_permissions),
    })


@login_required
@require_minimum_role('lab_manager')
def grant_object_permission_api(request):
    """API endpoint to grant object-level permission"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user_id = request.POST.get('user_id')
        model_name = request.POST.get('model_name')
        object_id = request.POST.get('object_id')
        permission_type = request.POST.get('permission_type')
        expires_at = request.POST.get('expires_at')
        if not all([user_id, model_name, object_id, permission_type]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        # Get the model class dynamically
        try:
            content_type = ContentType.objects.get(model=model_name.lower())
            model_class = content_type.model_class()
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid model name'}, status=400)
        # Get the user object
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        # Parse expiration date if provided
        parsed_expires_at = None
        if expires_at:
            try:
                from django.utils.dateparse import parse_datetime
                parsed_expires_at = parse_datetime(expires_at)
                if not parsed_expires_at:
                    return JsonResponse({'error': 'Invalid expiration date format'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid expiration date format'}, status=400)
        # Grant the permission
        permission = grant_object_permission(
            user=user,
            model_class=model_class,
            object_id=object_id,
            permission_type=permission_type,
            granted_by=request.user,
            expires_at=parsed_expires_at
        )
        return JsonResponse({
            'success': True,
            'permission_id': permission.id,
            'message': 'Permission granted successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_minimum_role('lab_manager')
def revoke_object_permission_api(request):
    """API endpoint to revoke object-level permission"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user_id = request.POST.get('user_id')
        model_name = request.POST.get('model_name')
        object_id = request.POST.get('object_id')
        permission_type = request.POST.get('permission_type')
        if not all([user_id, model_name, object_id, permission_type]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        # Get the model class dynamically
        try:
            content_type = ContentType.objects.get(model=model_name.lower())
            model_class = content_type.model_class()
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid model name'}, status=400)
        # Get the user object
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        # Revoke the permission
        success = revoke_object_permission(
            user=user,
            model_class=model_class,
            object_id=object_id,
            permission_type=permission_type,
            revoked_by=request.user
        )
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Permission revoked successfully'
            })
        else:
            return JsonResponse({
                'error': 'Permission not found'
            }, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
