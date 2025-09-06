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
        help_text='Upload a CSV file with sample data. Expected format: Source;Cell Line;Experiment #;Sample Notes;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Number of Aliquots Total;Disposition'
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
            proceed_with_import = request.POST.get('proceed_with_import', False)

            try:
                if proceed_with_import:
                    # Actual import
                    import_result = self.perform_import(csv_file)
                    details = import_result.get('details', {})
                    message = f'Successfully imported {import_result["total"]} records: '
                    message += f'{details.get("sources", 0)} sources, '
                    message += f'{details.get("samples", 0)} samples, '
                    message += f'{details.get("aliquots", 0)} aliquots, '
                    message += f'{details.get("tubes", 0)} tubes, '
                    message += f'{details.get("locations", 0)} locations'
                    messages.success(request, message)
                    return redirect('person:user_list')
                else:
                    # Preview mode (default for first submission)
                    preview_data = self.preview_import(csv_file)
                    context = self.get_context_data()
                    context['preview_data'] = preview_data
                    context['form'] = form
                    return render(request, self.template_name, context)

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
            # Save uploaded file temporarily
            temp_csv_path = f'/tmp/import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            with open(temp_csv_path, 'wb') as temp_file:
                for chunk in csv_file.chunks():
                    temp_file.write(chunk)

            # Use the existing convert_csv.py functionality
            fixtures = self.convert_csv_to_fixtures(temp_csv_path)

            # Count what would be imported
            preview_data['sources'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.source'])
            preview_data['samples'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.sample'])
            preview_data['aliquot_types'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquottype'])
            preview_data['dispositions'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquotdisposition'])
            preview_data['storage_items'] = set([f['fields']['name'] for f in fixtures if f['model'] in ['storage.site', 'storage.device', 'storage.shelf', 'storage.rack', 'storage.box']])
            preview_data['aliquots'] = len([f for f in fixtures if f['model'] == 'sample.aliquot'])
            preview_data['tubes'] = len([f for f in fixtures if f['model'] == 'sample.aliquottube'])
            preview_data['locations'] = len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])

            # Convert sets to sorted lists for display
            for key in ['sources', 'samples', 'storage_items', 'aliquot_types', 'dispositions']:
                preview_data[key] = sorted(list(preview_data[key]))

            # Clean up temporary file
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)

        except Exception as e:
            # Clean up temporary file on error
            if 'temp_csv_path' in locals() and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            raise Exception(f"Error reading CSV file: {str(e)}")

        return preview_data

    def perform_import(self, csv_file):
        """Actually perform the import"""
        try:
            # Save uploaded file temporarily
            temp_csv_path = f'/tmp/import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            with open(temp_csv_path, 'wb') as temp_file:
                for chunk in csv_file.chunks():
                    temp_file.write(chunk)

            # Use the existing convert_csv.py functionality
            fixtures = self.convert_csv_to_fixtures(temp_csv_path)

            # Save fixtures to temporary file
            fixtures_file = f'/tmp/import_fixtures_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(fixtures_file, 'w') as f:
                json.dump(fixtures, f, indent=2)

            # Use Django's loaddata command to import the fixtures
            from django.core.management import call_command
            from django.core.management.base import CommandError

            try:
                # Add debug logging
                print(f"Attempting to import {len(fixtures)} fixtures from {fixtures_file}")

                # Import fixtures using Django's loaddata command
                call_command('loaddata', fixtures_file, verbosity=1)

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
                    'tubes': len([f for f in fixtures if f['model'] == 'sample.aliquottube']),
                    'locations': len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])
                }

                total_imported = sum(import_counts.values())
                print(f"Successfully imported {total_imported} objects")

                # Clean up temporary files
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                if os.path.exists(temp_csv_path):
                    os.remove(temp_csv_path)

                return {
                    'total': total_imported,
                    'details': import_counts
                }

            except CommandError as e:
                # Clean up temporary files on error
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                if os.path.exists(temp_csv_path):
                    os.remove(temp_csv_path)
                print(f"CommandError during import: {str(e)}")
                raise Exception(f"Django import failed: {str(e)}")

            except Exception as e:
                # Clean up temporary files on any other error
                if os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                if os.path.exists(temp_csv_path):
                    os.remove(temp_csv_path)
                print(f"Unexpected error during import: {str(e)}")
                raise Exception(f"Unexpected import error: {str(e)}")

        except Exception as e:
            raise Exception(f"Import failed: {str(e)}")

    def convert_csv_to_fixtures(self, csv_file_path):
        """Convert CSV file to Django fixtures using the existing convert_csv.py logic"""
        fixtures = []
        pk_counter = defaultdict(lambda: 1)

        # Mapping dictionaries to track created objects
        sources = {}
        samples = {}
        storage = {'sites': {}, 'devices': {}, 'shelves': {}, 'racks': {}, 'boxes': {}}
        aliquot_types = {}
        dispositions = {}

        # Read CSV file
        with open(csv_file_path, 'r') as f:
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
                        'pk': samples[sample_key],
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
                site_name = 'Sikora Lab'
                freezer_name = row['Freezer Name']
                shelf_name = row['Position 2']  # e.g., "F"
                rack_name = row['Position 1']   # e.g., "4"
                box_name = f"{rack_name}_{shelf_name}"  # e.g., "4_F"

                if site_name not in storage['sites']:
                    storage['sites'][site_name] = pk_counter['site']
                    fixtures.append({
                        'model': 'storage.site',
                        'pk': storage['sites'][site_name],
                        'fields': {'name': site_name}
                    })
                    pk_counter['site'] += 1

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

                if shelf_name and rack_name:
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

                    # Create Rack if not exists
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

                    # Create Box if not exists
                    box_key = box_name
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
                            'disposition_type': disp_type
                        }
                    })
                    pk_counter['disposition'] += 1

                # Create Aliquot
                aliquot_pk = pk_counter['aliquot']
                # Use "Number of Aliquots Total" or "Collef Aliquots Total" for tube count
                quantity = int(float(row.get('Number of Aliquots Total', row.get('Collef Aliquots Total', 1)) or 1))
                current_time = timezone.now().isoformat()
                fixtures.append({
                    'model': 'sample.aliquot',
                    'pk': aliquot_pk,
                    'fields': {
                        'parent': None,  # Could be mapped if needed
                        'sample': samples[sample_key],
                        'quantity': quantity,
                        'aliquot_type': aliquot_types[aliquot_type],
                        'access_level': 'all_members',
                        'created_at': current_time,
                        'updated_at': current_time,
                        'deleted': False
                    }
                })
                pk_counter['aliquot'] += 1

                # Create AliquotTube for each tube in the aliquot
                for tube_num in range(1, quantity + 1):
                    fixtures.append({
                        'model': 'sample.aliquottube',
                        'pk': pk_counter['tube'],
                        'fields': {
                            'aliquot': aliquot_pk,
                            'tube_number': tube_num,
                            'disposition': dispositions[disposition],
                            'created_at': current_time,
                            'updated_at': current_time
                        }
                    })
                    pk_counter['tube'] += 1

                # Create AliquotLocation if box exists (only for first tube)
                if box_key in storage['boxes'] and row.get('Position 3') and row.get('Position 4') and quantity > 0:
                    try:
                        row_pos = int(row['Position 3'])
                        col_pos = int(row['Position 4'])
                        if row_pos > 0 and col_pos > 0:  # Only create location for valid positions
                            fixtures.append({
                                'model': 'sample.aliquotlocation',
                                'pk': pk_counter['location'],
                                'fields': {
                                    'aliquot': aliquot_pk,
                                    'tube_number': 1,  # Store first tube in the location
                                    'box': storage['boxes'][box_key],
                                    'row': row_pos,
                                    'column': col_pos,
                                    'created_at': current_time,
                                    'updated_at': current_time
                                }
                            })
                            pk_counter['location'] += 1
                    except (ValueError, TypeError) as e:
                        # Log error but continue with import
                        print(f"Warning: Could not create location for aliquot {aliquot_pk}: {e}")

        return fixtures


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
