# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django import forms
from django.core.files.uploadedfile import UploadedFile
import csv
import json
from datetime import datetime
from collections import defaultdict
from .models import User, UserPreference, UserRole, Permission, UserAuditLog
from .forms import CustomUserCreationForm, CustomUserChangeForm


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


# Data Import Admin View
@method_decorator(staff_member_required, name='dispatch')
class DataImportView(TemplateView):
    template_name = 'admin/data_import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DataImportForm()
        context['title'] = 'Data Import'
        context['opts'] = {'app_label': 'person', 'model_name': 'dataimport'}
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
                    messages.success(request, f'Successfully imported {import_result["total"]} records')
                    return redirect('admin:index')
                    
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
            
            reader = csv.DictReader(decoded_file.splitlines(), delimiter=';')
            for row in reader:
                # Collect unique values
                if row.get('Source'):
                    preview_data['sources'].add(row['Source'])
                if row.get('Cell Line'):
                    preview_data['samples'].add(row['Cell Line'])
                if row.get('Freezer Name'):
                    preview_data['storage_items'].add(f"Freezer: {row['Freezer Name']}")
                if row.get('Position 1'):
                    preview_data['storage_items'].add(f"Rack: {row['Position 1']}")
                if row.get('Position 2'):
                    preview_data['storage_items'].add(f"Box: {row['Position 2']}")
                if row.get('Aliquot Type'):
                    preview_data['aliquot_types'].add(row['Aliquot Type'])
                if row.get('Disposition'):
                    preview_data['dispositions'].add(row['Disposition'])
                
                preview_data['aliquots'] += 1
                if row.get('Position 3') and row.get('Position 4'):
                    preview_data['locations'] += 1
            
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
            
            # Parse CSV and create fixtures
            fixtures = self.parse_csv_to_fixtures(decoded_file)
            
            # Save fixtures to file (this could be enhanced to directly create Django objects)
            fixtures_file = f'import_fixtures_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(fixtures_file, 'w') as f:
                json.dump(fixtures, f, indent=2)
            
            return {
                'total': len(fixtures),
                'sources': len([f for f in fixtures if f['model'] == 'sample.source']),
                'samples': len([f for f in fixtures if f['model'] == 'sample.sample']),
                'aliquots': len([f for f in fixtures if f['model'] == 'sample.aliquot']),
                'fixtures_file': fixtures_file
            }
            
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
                        'notes': row.get('Sample Notes', '') or ''
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
            aliquot_type = row.get('Aliquot Type') or 'Unknown'
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
            disposition = row.get('Disposition') or 'In Storage'
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
                    'parent': None,
                    'sample': samples.get(sample_key, 1),
                    'quantity': int(float(row.get('Current Amount', 0) or 0)),
                    'aliquotType': aliquot_types[aliquot_type],
                    'disposition': dispositions[disposition],
                    'passage': row.get('Aliquot/SubA Passage#', '0') or '0',
                    'experiment': row.get('Experiment #', '') or '',
                    'notes': row.get('Aliquot Notes', '') or ''
                }
            })
            pk_counter['aliquot'] += 1
            
            # Create AliquotLocation if box exists
            if box_key in storage['boxes'] and row.get('Position 3') and row.get('Position 4'):
                fixtures.append({
                    'model': 'sample.aliquotlocation',
                    'pk': pk_counter['location'],
                    'fields': {
                        'aliquot': aliquot_pk,
                        'box': storage['boxes'][box_key],
                        'row': int(row['Position 3']),
                        'column': int(row['Position 4'])
                    }
                })
                pk_counter['location'] += 1
        
        return fixtures


# Custom Admin Site
class KrillAdminSite(admin.AdminSite):
    site_header = "Krill Laboratory Management System"
    site_title = "Krill Admin"
    index_title = "Welcome to Krill Administration"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('data-import/', DataImportView.as_view(), name='data_import'),
        ]
        return custom_urls + urls


# Create custom admin site instance
admin_site = KrillAdminSite(name='krill_admin')

# Register models with custom admin site
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'role_display', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined', 'role__role')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role_display',)}),
    )
    readonly_fields = ('role_display',)
    
    def role_display(self, obj):
        if hasattr(obj, 'role'):
            role_colors = {
                'lab_admin': '#dc3545',  # Red
                'lab_manager': '#fd7e14',  # Orange
                'lab_member': '#28a745',  # Green
                'viewer': '#6c757d',  # Gray
            }
            color = role_colors.get(obj.role.role, '#6c757d')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.role.get_role_display()
            )
        return 'No Role'
    role_display.short_description = 'Role'


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'dark_mode', 'created_at')
    list_filter = ('dark_mode',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'lab_unit', 'created_at', 'updated_at')
    list_filter = ('role', 'department', 'lab_unit', 'created_at')
    search_fields = ('user__username', 'user__email', 'department', 'lab_unit')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role')
        }),
        ('Organization', {
            'fields': ('department', 'lab_unit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission_type', 'content_type', 'object_id', 'granted_by', 'granted_at', 'expires_at', 'is_valid')
    list_filter = ('permission_type', 'content_type', 'granted_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'granted_by__username')
    readonly_fields = ('granted_at', 'is_valid')
    date_hierarchy = 'granted_at'
    fieldsets = (
        ('Permission Details', {
            'fields': ('user', 'permission_type', 'content_type', 'object_id')
        }),
        ('Grant Information', {
            'fields': ('granted_by', 'granted_at', 'expires_at')
        }),
        ('Status', {
            'fields': ('is_valid',)
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'granted_by', 'content_type')


@admin.register(UserAuditLog)
class UserAuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'target_type', 'target_id', 'ip_address', 'timestamp')
    list_filter = ('action', 'target_type', 'timestamp', 'ip_address')
    search_fields = ('user__username', 'user__email', 'target_name', 'ip_address')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'target_name', 'details', 'ip_address', 'user_agent', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Target Information', {
            'fields': ('target_type', 'target_id', 'target_name')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def details_formatted(self, obj):
        if obj.details:
            formatted = []
            for key, value in obj.details.items():
                formatted.append(f"<strong>{key}:</strong> {value}")
            return mark_safe("<br>".join(formatted))
        return '-'
    details_formatted.short_description = 'Details'


# Register all models with the custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(UserPreference, UserPreferenceAdmin)
admin_site.register(UserRole, UserRoleAdmin)
admin_site.register(Permission, PermissionAdmin)
admin_site.register(UserAuditLog, UserAuditLogAdmin)

# Also register with the default admin site for backward compatibility
# (This keeps the existing admin functionality working)