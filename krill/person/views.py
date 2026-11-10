from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404, JsonResponse
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
import logging
import os
import re
import tempfile
import zipfile
from datetime import date, datetime
from collections import defaultdict

logger = logging.getLogger(__name__)
User = get_user_model()
from .models import UserPreference, UserRole, Permission, UserAuditLog
from .forms import (
    UserRoleForm, PermissionForm, UserPreferenceForm,
    BulkPermissionForm, UserSearchForm, AuditLogFilterForm, CreateUserForm,
    PasswordChangeForm
)
from .decorators import require_permission, require_minimum_role, grant_object_permission, revoke_object_permission
from .utils import get_upload_temp_dir

# Column headers the importer reads. Uploaded headers are matched to these
# case-insensitively (and ignoring surrounding whitespace), since spreadsheets
# from Windows/Excel are often capitalized inconsistently.
IMPORT_COLUMNS = (
    'Source', 'Cell Line', 'Experiment #', 'Sample Notes', 'Site', 'Freezer Name',
    'Position 1', 'Position 2', 'Position 3', 'Position 4', 'Aliquot Type',
    'Number of Aliquots Total', 'Collef Aliquots Total', 'Disposition',
    'Passage Number', 'Lab Member', 'Sample date',
)


def normalize_import_headers(fieldnames):
    """Map uploaded CSV headers onto their canonical names, ignoring case.

    Unrecognized headers are returned unchanged. If two headers collapse to the
    same canonical name, only the first is renamed.
    """
    canonical = {name.casefold(): name for name in IMPORT_COLUMNS}
    result, used = [], set()
    for header in fieldnames or []:
        name = canonical.get((header or '').strip().casefold())
        if name is not None and name not in used:
            used.add(name)
            result.append(name)
        else:
            result.append(header)
    return result


# How Position 1 and Position 2 map onto the storage hierarchy. The sheet does not say,
# so whoever imports chooses.
LAYOUT_FREEZER = 'freezer'   # Position 2 = shelf, Position 1 = rack, on that shelf
LAYOUT_DEWAR = 'dewar'       # a dewar has one shelf: Position 1 = cane (rack), Position 2 = box letter
STORAGE_LAYOUT_CHOICES = [
    (LAYOUT_FREEZER, 'Freezer with shelves (Position 2 is the shelf, Position 1 the rack)'),
    (LAYOUT_DEWAR, 'Dewar with canes (Position 1 is the cane, Position 2 the box on it; one shelf)'),
]
DEWAR_SHELF_NAME = 'Canes'

# Boxes are 9x9 unless the sheet places a tube beyond that.
DEFAULT_BOX_SIZE = 9

# Columns that only say where a tube is and what kind it is. A row with a value in
# none of the *other* columns carries no sample information (typically an empty slot
# in a pre-filled box grid) and is skipped on import.
LOCATION_COLUMNS = frozenset({
    'Site', 'Freezer Name', 'Position 1', 'Position 2', 'Position 3', 'Position 4', 'Aliquot Type',
})


def is_location_only_row(row):
    """True if every column outside LOCATION_COLUMNS is blank."""
    for key, value in row.items():
        if key in LOCATION_COLUMNS:
            continue
        values = value if isinstance(value, list) else [value]  # DictReader puts extra cells in a list
        if any(str(v).strip() for v in values if v is not None):
            return False
    return True


def is_note_row(row):
    """True for a row with no cell line and no storage location at all.

    These are comments typed into the sheet (e.g. "COMPLETE BOX H MISSING" in the
    Experiment # column), not tubes, so they are skipped on import.
    """
    def blank(key):
        return not str(row.get(key) or '').strip()

    return blank('Cell Line') and all(
        blank(key) for key in ('Site', 'Freezer Name', 'Position 1', 'Position 2', 'Position 3', 'Position 4')
    )


def parse_sample_date(text):
    """Parse a sample date from a spreadsheet cell.

    Returns (date, ok). Blank text is (None, True). Month-only values such as
    "7/2021" or "Jul-21" become the 1st of that month. Anything unrecognized is
    (None, False) so the caller can report it rather than guess.
    """
    text = (text or '').strip()
    if not text:
        return None, True
    month_only = re.fullmatch(r'(\d{1,2})/(\d{4})', text)
    if month_only:
        try:
            return date(int(month_only.group(2)), int(month_only.group(1)), 1), True
        except ValueError:
            return None, False
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(text, fmt).date(), True
        except ValueError:
            pass
    try:
        return datetime.strptime(text, '%b-%y').date().replace(day=1), True
    except ValueError:
        return None, False


class ImportConflictError(ValueError):
    """The file cannot be added to the current data (e.g. a storage slot is taken).

    `conflicts` lists every refused item as a dict with `box`, `row`, `column`,
    `cell_line` and `reason`, so the page can show exactly what was refused and why.
    """

    def __init__(self, message, conflicts=()):
        super().__init__(message)
        self.conflicts = list(conflicts)


def summarize_conflicts(conflicts, examples=3):
    """Group refused items by box and reason: [{box, reason, count, cell_lines}], largest first."""
    groups = {}
    for conflict in conflicts:
        kind = ('Slot already holds an aliquot in Krill' if conflict['existing_sample'] is not None
                else 'Slot used by more than one row in this file')
        group = groups.setdefault((conflict['box'], kind), {'box': conflict['box'], 'reason': kind, 'count': 0, 'names': []})
        group['count'] += 1
        name = conflict['cell_line'] or '(no cell line)'
        if name not in group['names']:
            group['names'].append(name)
    summary = []
    for group in groups.values():
        shown = group['names'][:examples]
        extra = len(group['names']) - len(shown)
        summary.append({
            'box': group['box'], 'reason': group['reason'], 'count': group['count'],
            'cell_lines': ', '.join(shown) + (f' and {extra} more' if extra > 0 else ''),
        })
    return sorted(summary, key=lambda g: (-g['count'], g['box']))


def normalize_sample_name(name):
    """Key used to match cell lines: ignores case and surrounding whitespace."""
    return (name or '').strip().casefold()


def load_existing_import_context():
    """Read what the import must build on: existing rows by natural key, the next free
    primary key per model, and the storage slots that are already occupied.

    Names are matched exactly. Shelves and boxes are matched by name within their
    freezer and racks by name within their shelf, which preserves how earlier imports
    shaped the hierarchy.
    """
    from django.db.models import Max
    from sample.models.source import Source
    from sample.models.sample import Sample
    from sample.models.aliquot import Aliquot, AliquotLocation, AliquotType, AliquotDisposition
    from storage.models.site import Site
    from storage.models.storage import Device, Shelf, Rack, Box

    def first_by_name(queryset):
        found = {}
        for pk, name in queryset.order_by('pk').values_list('pk', 'name'):
            found.setdefault(name, pk)
        return found

    def next_pk(model):
        return (model.objects.aggregate(top=Max('pk'))['top'] or 0) + 1

    def scoped(queryset, scope_path):
        found = {}
        for pk, name, scope in queryset.order_by('pk').values_list('pk', 'name', scope_path):
            found.setdefault((scope, name), pk)
        return found

    return {
        'sources': first_by_name(Source.objects),
        'samples': {
            normalize_sample_name(name): pk
            for pk, name in reversed(list(Sample.objects.order_by('pk').values_list('pk', 'name')))
        },   # lowest pk wins for names that differ only by case/spacing
        'aliquot_types': first_by_name(AliquotType.objects),
        'dispositions': first_by_name(AliquotDisposition.objects),
        'sites': first_by_name(Site.objects),
        'devices': scoped(Device.objects, 'site_id'),
        'shelves': scoped(Shelf.objects, 'device_id'),
        'racks': scoped(Rack.objects, 'shelf_id'),
        'boxes': scoped(Box.objects, 'rack__shelf__device_id'),
        'occupied_slots': {
            (box_id, row, column): ('existing', aliquot_id, sample_name)
            for box_id, row, column, aliquot_id, sample_name in AliquotLocation.objects.values_list(
                'box_id', 'row', 'column', 'aliquot_id', 'aliquot__sample__name')
        },
        'next_pk': {
            'source': next_pk(Source), 'sample': next_pk(Sample),
            'aliquot_type': next_pk(AliquotType), 'disposition': next_pk(AliquotDisposition),
            'site': next_pk(Site), 'device': next_pk(Device), 'shelf': next_pk(Shelf),
            'rack': next_pk(Rack), 'box': next_pk(Box),
            'aliquot': next_pk(Aliquot), 'location': next_pk(AliquotLocation),
        },
    }


def _xlsx_cell_to_text(value):
    """Render an XLSX cell the way it would appear in a CSV export."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(sep=' ')
    return str(value)


def xlsx_to_csv(xlsx_path, dest_dir=None):
    """Convert the first sheet of an XLSX workbook to a temporary tab-delimited CSV.

    Returns the path of the new file; the caller is responsible for removing it.
    Blank rows are skipped. Formulas are read as their last saved value.
    """
    from openpyxl import load_workbook

    fd, csv_path = tempfile.mkstemp(suffix='.csv', dir=dest_dir)
    try:
        # Pass a file object: uploads are stored as *.csv regardless of type, and
        # openpyxl rejects paths by extension.
        with open(xlsx_path, 'rb') as source, os.fdopen(fd, 'w', newline='', encoding='utf-8') as out:
            workbook = load_workbook(source, read_only=True, data_only=True)
            try:
                writer = csv.writer(out, delimiter='\t')
                for row in workbook.worksheets[0].iter_rows(values_only=True):
                    cells = [_xlsx_cell_to_text(value) for value in row]
                    if any(cell.strip() for cell in cells):
                        writer.writerow(cells)
            finally:
                workbook.close()
    except Exception:
        os.remove(csv_path)
        raise
    return csv_path


def is_xlsx_file(path):
    """True if the file is an XLSX workbook (checked by content, not extension)."""
    return zipfile.is_zipfile(path)



# Data Import Form
class DataImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Data File',
        help_text='Upload a CSV or XLSX file with sample data (for XLSX, the first sheet is used). Expected columns: Source;Cell Line;Experiment #;Sample Notes;Site;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Number of Aliquots Total;Disposition (Site is optional, defaults to "Default Site")'
    )

    storage_layout = forms.ChoiceField(
        label='Storage layout',
        choices=STORAGE_LAYOUT_CHOICES,
        initial=LAYOUT_FREEZER,
        required=False,   # left out (e.g. by a script) means the freezer layout
        widget=forms.RadioSelect,
        help_text='How the Position 1 and Position 2 columns map onto the storage hierarchy. Applies to the whole file.',
    )

    def clean_storage_layout(self):
        return self.cleaned_data.get('storage_layout') or LAYOUT_FREEZER

    def clean_csv_file(self):
        uploaded = self.cleaned_data['csv_file']
        if uploaded.name.lower().endswith('.xls'):
            raise forms.ValidationError(
                'Legacy .xls files are not supported. Save the file as .xlsx or CSV and upload it again.'
            )
        return uploaded


# Data Import View for main app
@method_decorator(require_minimum_role('lab_manager'), name='dispatch')
class DataImportView(TemplateView):
    template_name = 'person/data_import.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DataImportForm()
        context['title'] = 'Data Import'
        return context

    def post(self, request, *args, **kwargs):
        form = DataImportForm(request.POST, request.FILES)
        proceed_with_import = request.POST.get('proceed_with_import', False)

        # "Proceed with Import" submits only import_id (no file); handle it without requiring form validation
        if proceed_with_import:
            import_id = request.POST.get('import_id', '').strip()
            if not import_id:
                messages.error(request, 'Import session expired. Please upload your file again.')
                return redirect('person:data_import')

            csv_file = self.get_temp_file(import_id, request.user.id)
            if not csv_file:
                messages.error(request, 'Import file not found. Please upload your file again.')
                return redirect('person:data_import')

            storage_layout = request.POST.get('storage_layout', '').strip()
            if storage_layout not in (LAYOUT_FREEZER, LAYOUT_DEWAR):
                storage_layout = LAYOUT_FREEZER

            try:
                logger.info(f"Starting data import for user {request.user.username}")

                import_result = self.perform_import(csv_file, storage_layout)
                details = import_result.get('details', {})
                message = f'Successfully imported {import_result["total"]} records: '
                message += f'{details.get("sources", 0)} sources, '
                message += f'{details.get("samples", 0)} samples, '
                message += f'{details.get("aliquots", 0)} aliquots, '
                message += f'{details.get("tubes", 0)} tubes, '
                message += f'{details.get("locations", 0)} locations'

                logger.info(f"Import completed successfully: {message}")

                self.cleanup_temp_file(import_id, request.user.id)

                messages.success(request, message)
                return redirect('person:user_list')
            except Exception as e:
                logger.error(f"Import failed for user {request.user.username}: {str(e)}", exc_info=True)
                self.cleanup_temp_file(import_id, request.user.id)
                messages.error(request, f'Import failed: {str(e)}')
                context = self.get_context_data()
                context['form'] = DataImportForm()
                context['error'] = str(e)
                context.update(self.conflict_context(e, request.user.id))
                return render(request, self.template_name, context)

        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            import_id = None  # only set after store_temp_file(); used for cleanup on error
            try:
                # Preview mode - store file temporarily and generate import ID
                import_id = self.store_temp_file(csv_file, request.user.id)

                # Reset file pointer for preview
                csv_file.seek(0)

                preview_data = self.preview_import(csv_file, form.cleaned_data['storage_layout'])
                context = self.get_context_data()
                context['preview_data'] = preview_data
                context['form'] = form
                context['import_id'] = import_id
                context['storage_layout'] = form.cleaned_data['storage_layout']
                context['file_stored'] = True
                return render(request, self.template_name, context)

            except Exception as e:
                logger.error(f"Import failed for user {request.user.username}: {str(e)}", exc_info=True)
                if import_id:
                    self.cleanup_temp_file(import_id, request.user.id)
                messages.error(request, f'Import failed: {str(e)}')
                context = self.get_context_data()
                context['form'] = form
                context['error'] = str(e)
                context.update(self.conflict_context(e, request.user.id))
                return render(request, self.template_name, context)

        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)

    def preview_import(self, csv_file, storage_layout=LAYOUT_FREEZER):
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
            temp_dir = get_upload_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)

            temp_csv_path = os.path.join(temp_dir, f'import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            with open(temp_csv_path, 'wb') as temp_file:
                for chunk in csv_file.chunks():
                    temp_file.write(chunk)

            # Use the existing convert_csv.py functionality
            fixtures = self.convert_csv_to_fixtures(temp_csv_path, storage_layout)

            # Count what would be imported
            preview_data['sources'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.source'])
            preview_data['samples'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.sample'])
            preview_data['aliquot_types'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquottype'])
            preview_data['dispositions'] = set([f['fields']['name'] for f in fixtures if f['model'] == 'sample.aliquotdisposition'])
            preview_data['storage_items'] = set([f['fields']['name'] for f in fixtures if f['model'] in ['storage.site', 'storage.device', 'storage.shelf', 'storage.rack', 'storage.box']])
            preview_data['aliquots'] = len([f for f in fixtures if f['model'] == 'sample.aliquot'])
            preview_data['tubes'] = 0  # No longer separate; each aliquot is one physical item
            preview_data['locations'] = len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])
            preview_data['skipped_rows'] = getattr(self, 'skipped_empty_rows', 0)
            preview_data['unparsed_dates'] = getattr(self, 'unparsed_sample_dates', 0)
            reused = getattr(self, 'reused_counts', {})
            preview_data['reused'] = [
                (label, reused[key]) for key, label in (
                    ('sources', 'sources'), ('samples', 'samples'), ('aliquot_types', 'aliquot types'),
                    ('dispositions', 'dispositions'), ('sites', 'sites'), ('devices', 'freezers'),
                    ('shelves', 'shelves'), ('racks', 'racks'), ('boxes', 'boxes'),
                ) if reused.get(key)
            ]

            # Convert sets to sorted lists for display
            for key in ['sources', 'samples', 'storage_items', 'aliquot_types', 'dispositions']:
                preview_data[key] = sorted(list(preview_data[key]))

            # Clean up temporary file
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)

        except ImportConflictError:
            if 'temp_csv_path' in locals() and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            raise
        except Exception as e:
            # Clean up temporary file on error
            if 'temp_csv_path' in locals() and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            raise Exception(f"Error reading CSV file: {str(e)}")

        return preview_data

    def store_temp_file(self, csv_file, user_id):
        """Store uploaded file temporarily and return import ID"""
        import uuid
        import hashlib
        from django.conf import settings

        # Check file size limit (default 10MB, configurable)
        max_size = getattr(settings, 'MAX_IMPORT_FILE_SIZE', 10 * 1024 * 1024)  # 10MB
        if csv_file.size > max_size:
            raise Exception(f"File too large. Maximum size allowed is {max_size / 1024 / 1024:.1f}MB")

        # Generate unique import ID
        import_id = str(uuid.uuid4())

        temp_dir = get_upload_temp_dir()
        os.makedirs(temp_dir, exist_ok=True)

        # Create user-specific subdirectory for security
        user_temp_dir = os.path.join(temp_dir, f'imports_{user_id}')
        os.makedirs(user_temp_dir, exist_ok=True)

        # Store file with import ID
        temp_file_path = os.path.join(user_temp_dir, f'{import_id}.csv')

        with open(temp_file_path, 'wb') as temp_file:
            for chunk in csv_file.chunks():
                temp_file.write(chunk)

        # Store metadata (file name, size, timestamp)
        metadata = {
            'filename': csv_file.name,
            'size': csv_file.size,
            'timestamp': timezone.now().isoformat(),
            'user_id': user_id
        }

        metadata_path = os.path.join(user_temp_dir, f'{import_id}.meta')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        return import_id

    def get_temp_file(self, import_id, user_id):
        """Retrieve temporary file by import ID"""
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO

        temp_dir = get_upload_temp_dir()
        user_temp_dir = os.path.join(temp_dir, f'imports_{user_id}')
        temp_file_path = os.path.join(user_temp_dir, f'{import_id}.csv')
        metadata_path = os.path.join(user_temp_dir, f'{import_id}.meta')

        if not os.path.exists(temp_file_path) or not os.path.exists(metadata_path):
            return None

        try:
            # Read metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Read file data
            with open(temp_file_path, 'rb') as f:
                file_data = f.read()

            # Recreate InMemoryUploadedFile
            csv_file = InMemoryUploadedFile(
                BytesIO(file_data),
                None,
                metadata['filename'],
                'text/csv',
                len(file_data),
                None
            )

            return csv_file

        except Exception as e:
            logger.error(f"Error retrieving temp file {import_id}: {e}")
            return None

    def conflict_context(self, error, user_id):
        """Template context for a refused import: aggregate list plus a CSV download token."""
        if not isinstance(error, ImportConflictError) or not error.conflicts:
            return {}
        token = self.store_refusals(error.conflicts, user_id)
        return {
            'conflict_summary': summarize_conflicts(error.conflicts),
            'conflict_total': len(error.conflicts),
            'refusals_token': token,
        }

    def store_refusals(self, conflicts, user_id):
        """Write every refused item to a CSV the user can download; returns its token."""
        import uuid
        token = uuid.uuid4().hex
        user_dir = os.path.join(get_upload_temp_dir(), f'imports_{user_id}')
        os.makedirs(user_dir, exist_ok=True)
        with open(os.path.join(user_dir, f'refused_{token}.csv'), 'w', newline='', encoding='utf-8') as out:
            writer = csv.writer(out)
            writer.writerow(['Box', 'Row', 'Column', 'Cell line', 'Why refused'])
            for c in conflicts:
                writer.writerow([c['box'], c['row'], c['column'], c['cell_line'], c['reason']])
        return token

    def cleanup_temp_file(self, import_id, user_id):
        """Clean up temporary file and metadata"""
        temp_dir = get_upload_temp_dir()
        user_temp_dir = os.path.join(temp_dir, f'imports_{user_id}')
        temp_file_path = os.path.join(user_temp_dir, f'{import_id}.csv')
        metadata_path = os.path.join(user_temp_dir, f'{import_id}.meta')

        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
        except Exception as e:
            logger.error(f"Error cleaning up temp file {import_id}: {e}")

    def perform_import(self, csv_file, storage_layout=LAYOUT_FREEZER):
        """Actually perform the import"""
        temp_csv_path = None
        fixtures_file = None

        try:
            temp_dir = get_upload_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)

            # Save uploaded file temporarily
            temp_csv_path = os.path.join(temp_dir, f'import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            with open(temp_csv_path, 'wb') as temp_file:
                for chunk in csv_file.chunks():
                    temp_file.write(chunk)

            # Use the existing convert_csv.py functionality
            fixtures = self.convert_csv_to_fixtures(temp_csv_path, storage_layout)

            # Save fixtures to temporary file
            fixtures_file = os.path.join(temp_dir, f'import_fixtures_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(fixtures_file, 'w') as f:
                json.dump(fixtures, f, indent=2)

            # Use Django's loaddata command to import the fixtures
            from django.core.management import call_command
            from django.core.management.base import CommandError

            try:
                # Add debug logging
                logger.info(f"Attempting to import {len(fixtures)} fixtures from {fixtures_file}")
                print(f"Attempting to import {len(fixtures)} fixtures from {fixtures_file}")

                # Import fixtures using Django's loaddata command with better error handling
                from io import StringIO
                import sys

                # Capture output from loaddata command
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                try:
                    call_command('loaddata', fixtures_file, verbosity=2)
                    output = captured_output.getvalue()
                    logger.info(f"Loaddata output: {output}")
                    print(f"Loaddata output: {output}")
                finally:
                    sys.stdout = old_stdout

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
                    'tubes': 0,  # No longer separate; each aliquot is one physical item
                    'locations': len([f for f in fixtures if f['model'] == 'sample.aliquotlocation'])
                }

                total_imported = sum(import_counts.values())
                logger.info(f"Successfully imported {total_imported} objects")
                print(f"Successfully imported {total_imported} objects")

                # Clean up temporary files
                if fixtures_file and os.path.exists(fixtures_file):
                    os.remove(fixtures_file)
                if temp_csv_path and os.path.exists(temp_csv_path):
                    os.remove(temp_csv_path)

                return {
                    'total': total_imported,
                    'details': import_counts
                }

            except CommandError as e:
                logger.error(f"CommandError during import: {str(e)}")
                print(f"CommandError during import: {str(e)}")
                raise Exception(f"Django import failed: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error during import: {str(e)}")
                print(f"Unexpected error during import: {str(e)}")
                raise Exception(f"Unexpected import error: {str(e)}")

        except ImportConflictError:
            if fixtures_file and os.path.exists(fixtures_file):
                os.remove(fixtures_file)
            if temp_csv_path and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            raise
        except Exception as e:
            # Clean up temporary files on any error
            if fixtures_file and os.path.exists(fixtures_file):
                os.remove(fixtures_file)
            if temp_csv_path and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            raise Exception(f"Import failed: {str(e)}")

    def convert_csv_to_fixtures(self, csv_file_path, storage_layout=LAYOUT_FREEZER):
        """Convert an uploaded CSV or XLSX file to Django fixtures."""
        self.storage_layout = storage_layout
        if not is_xlsx_file(csv_file_path):
            return self._convert_csv_to_fixtures(csv_file_path)

        converted_path = xlsx_to_csv(csv_file_path, dest_dir=os.path.dirname(csv_file_path))
        try:
            return self._convert_csv_to_fixtures(converted_path)
        finally:
            if os.path.exists(converted_path):
                os.remove(converted_path)

    @staticmethod
    def _conflict_summary(conflicts):
        """One-paragraph explanation of a refused import (the full list is shown separately)."""
        in_krill = sum(1 for c in conflicts if c['existing_sample'] is not None)
        in_file = len(conflicts) - in_krill
        parts = []
        if in_krill:
            parts.append(f"{in_krill} already hold aliquots in Krill")
        if in_file:
            parts.append(f"{in_file} are used by more than one row in this file")
        summary = (
            f"Import refused, nothing was changed: {len(conflicts)} storage slot(s) cannot be used "
            f"({'; '.join(parts)})."
        )
        if in_krill == len(conflicts) and all(normalize_sample_name(c['existing_sample']) == normalize_sample_name(c['cell_line']) for c in conflicts):
            summary += " Every refused row matches an aliquot already in those slots, so this file has probably already been imported."
        return summary

    def _convert_csv_to_fixtures(self, csv_file_path):
        """Convert CSV file to Django fixtures using the existing convert_csv.py logic"""
        fixtures = []
        self.skipped_empty_rows = 0
        self.unparsed_sample_dates = 0

        # Build on the current data: rows that already exist (matched by name) are reused
        # and get no fixture, and new rows are numbered after the highest existing id so
        # loading never overwrites anything.
        existing = load_existing_import_context()
        pk_counter = defaultdict(lambda: 1, existing['next_pk'])
        occupied_slots = dict(existing['occupied_slots'])   # slot -> who holds it
        slot_conflicts = []
        box_extent = {}   # box pk -> [highest row, highest column] used in this file
        reused = {name: set() for name in
                  ('sources', 'samples', 'aliquot_types', 'dispositions', 'sites', 'devices', 'shelves', 'racks', 'boxes')}

        # Mapping dictionaries: natural key -> primary key (existing or newly created)
        sources = dict(existing['sources'])
        samples = dict(existing['samples'])
        storage = {
            'sites': dict(existing['sites']), 'devices': dict(existing['devices']),
            'shelves': dict(existing['shelves']), 'racks': dict(existing['racks']),
            'boxes': dict(existing['boxes']),
        }
        aliquot_types = dict(existing['aliquot_types'])
        dispositions = dict(existing['dispositions'])
        self.reused_counts = {}

        required_columns = {'Source', 'Cell Line', 'Freezer Name', 'Position 1', 'Position 2', 'Aliquot Type', 'Disposition'}

        # Detect encoding: honour BOM if present, otherwise try UTF-8 then fall back to latin-1
        with open(csv_file_path, 'rb') as f:
            raw_start = f.read(4)
        if raw_start.startswith((b'\xef\xbb\xbf',)):
            encoding = 'utf-8-sig'
        elif raw_start.startswith((b'\xff\xfe', b'\xfe\xff')):
            encoding = 'utf-16'
        else:
            try:
                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    f.read(4096)
                encoding = 'utf-8'
            except UnicodeDecodeError:
                encoding = 'latin-1'

        # Read CSV file
        with open(csv_file_path, 'r', encoding=encoding) as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ';'
            reader = csv.DictReader(f, delimiter=delimiter)
            reader.fieldnames = normalize_import_headers(reader.fieldnames)
            for row in reader:
                missing = required_columns - row.keys()
                if missing:
                    raise KeyError(f"Missing required columns: {sorted(missing)}. Found: {sorted(row.keys())}")
                if is_location_only_row(row) or is_note_row(row):
                    self.skipped_empty_rows += 1
                    continue
                # Create Source if not exists
                source_name = row['Source'] or 'Unknown'
                if source_name in existing['sources']:
                    reused['sources'].add(source_name)
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
                # Cell lines match ignoring case and surrounding whitespace ("MM134", "mm134 ");
                # a new sample keeps the first spelling seen, trimmed.
                sample_name = (row['Cell Line'] or '').strip()
                sample_key = normalize_sample_name(sample_name)
                current_notes = row['Sample Notes'] or ''
                if sample_key in existing['samples']:
                    reused['samples'].add(sample_key)
                if sample_key not in samples:
                    samples[sample_key] = pk_counter['sample']
                    fixtures.append({
                        'model': 'sample.sample',
                        'pk': samples[sample_key],
                        'fields': {
                            'name': sample_name,
                            'experiment': row['Experiment #'] or '',
                            'source': sources[source_name],
                            'notes': current_notes
                        }
                    })
                    pk_counter['sample'] += 1
                else:
                    # Sample exists, check if we need to append notes
                    existing_sample = next((fixture for fixture in fixtures if fixture['model'] == 'sample.sample' and fixture['pk'] == samples[sample_key]), None)
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
                rack_name = row['Position 1']   # e.g., "4"
                box_letter = row['Position 2']  # e.g., "F"
                box_name = f"{rack_name}_{box_letter}"  # e.g., "4_F"
                # Freezer: Position 2 is the shelf. Dewar: one shelf holds every cane (Position 1).
                shelf_name = DEWAR_SHELF_NAME if getattr(self, 'storage_layout', LAYOUT_FREEZER) == LAYOUT_DEWAR else box_letter

                if site_name in existing['sites']:
                    reused['sites'].add(site_name)
                if site_name not in storage['sites']:
                    storage['sites'][site_name] = pk_counter['site']
                    fixtures.append({
                        'model': 'storage.site',
                        'pk': storage['sites'][site_name],
                        'fields': {'name': site_name}
                    })
                    pk_counter['site'] += 1
                site_pk = storage['sites'][site_name]

                # Freezer, shelf, rack and box are matched by name within their parent
                # (shelf, rack and box within the freezer) and created when missing.
                device_pk = None
                box_key = None
                if freezer_name:
                    device_key = (site_pk, freezer_name)
                    if device_key in existing['devices']:
                        reused['devices'].add(device_key)
                    if device_key not in storage['devices']:
                        storage['devices'][device_key] = pk_counter['device']
                        fixtures.append({
                            'model': 'storage.device',
                            'pk': storage['devices'][device_key],
                            'fields': {
                                'name': freezer_name,
                                'description': '',
                                'site': site_pk
                            }
                        })
                        pk_counter['device'] += 1
                    device_pk = storage['devices'][device_key]

                if device_pk is not None and box_letter and rack_name:
                    shelf_key = (device_pk, shelf_name)
                    if shelf_key in existing['shelves']:
                        reused['shelves'].add(shelf_key)
                    if shelf_key not in storage['shelves']:
                        storage['shelves'][shelf_key] = pk_counter['shelf']
                        fixtures.append({
                            'model': 'storage.shelf',
                            'pk': storage['shelves'][shelf_key],
                            'fields': {
                                'name': shelf_name,
                                'description': '',
                                'device': device_pk
                            }
                        })
                        pk_counter['shelf'] += 1

                    rack_key = (storage['shelves'][shelf_key], rack_name)
                    if rack_key in existing['racks']:
                        reused['racks'].add(rack_key)
                    if rack_key not in storage['racks']:
                        storage['racks'][rack_key] = pk_counter['rack']
                        fixtures.append({
                            'model': 'storage.rack',
                            'pk': storage['racks'][rack_key],
                            'fields': {
                                'name': rack_name,
                                'description': '',
                                'shelf': storage['shelves'][shelf_key]
                            }
                        })
                        pk_counter['rack'] += 1

                    box_key = (device_pk, box_name)
                    if box_key in existing['boxes']:
                        reused['boxes'].add(box_key)
                    if box_key not in storage['boxes']:
                        storage['boxes'][box_key] = pk_counter['box']
                        fixtures.append({
                            'model': 'storage.box',
                            'pk': storage['boxes'][box_key],
                            'fields': {
                                'name': box_name,
                                'description': '',
                                'rack': storage['racks'][rack_key],
                                'rows': DEFAULT_BOX_SIZE,
                                'columns': DEFAULT_BOX_SIZE
                            }
                        })
                        pk_counter['box'] += 1

                # Create AliquotType if not exists
                aliquot_type = row['Aliquot Type'] or 'Unknown'
                if aliquot_type in existing['aliquot_types']:
                    reused['aliquot_types'].add(aliquot_type)
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
                    # Legacy CSV aliases
                    'In Storage': 'stored',
                    'Used': 'exhausted',
                    'Checked Out': 'in_use',
                    'Disposed': 'disposed',
                    # Model values accepted directly
                    'stored': 'stored',
                    'in_use': 'in_use',
                    'exhausted': 'exhausted',
                    'disposed': 'disposed',
                }
                disposition = row['Disposition'] or 'In Storage'
                disp_type = disposition_map.get(disposition, 'stored')
                if disposition in existing['dispositions']:
                    reused['dispositions'].add(disposition)
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

                # Create one Aliquot per physical item (new model: 1 row = N aliquots)
                # Use "Number of Aliquots Total" or "Collef Aliquots Total" for count
                quantity = int(float(row.get('Number of Aliquots Total', row.get('Collef Aliquots Total', 1)) or 1))
                current_time = timezone.now().isoformat()

                # Create N aliquot records, each representing one physical item
                first_aliquot_pk = pk_counter['aliquot']
                for aliquot_num in range(quantity):
                    aliquot_pk = pk_counter['aliquot']
                    sample_date, date_ok = parse_sample_date(row.get('Sample date'))
                    if not date_ok:
                        self.unparsed_sample_dates += 1
                    fixtures.append({
                        'model': 'sample.aliquot',
                        'pk': aliquot_pk,
                        'fields': {
                            'passage': (row.get('Passage Number') or '').strip(),
                            'sample_date': sample_date.isoformat() if sample_date else None,
                            'lab_member_initials': (row.get('Lab Member') or '').strip(),
                            'parent': None,  # Could be mapped if needed
                            'sample': samples[sample_key],
                            'disposition': dispositions[disposition],
                            'aliquot_type': aliquot_types[aliquot_type],
                            'access_level': 'all_members',
                            'created_at': current_time,
                            'updated_at': current_time,
                            'deleted': False
                        }
                    })
                    pk_counter['aliquot'] += 1

                # Create AliquotLocation if box exists (only for first aliquot in the batch)
                if box_key is not None and row.get('Position 3') and row.get('Position 4') and quantity > 0:
                    try:
                        row_pos = int(row['Position 3'])
                        col_pos = int(row['Position 4'])
                        if row_pos > 0 and col_pos > 0:  # Only create location for valid positions
                            extent = box_extent.setdefault(storage['boxes'][box_key], [0, 0])
                            extent[0], extent[1] = max(extent[0], row_pos), max(extent[1], col_pos)
                            slot = (storage['boxes'][box_key], row_pos, col_pos)
                            if slot in occupied_slots:
                                holder = occupied_slots[slot]
                                if holder[0] == 'existing':
                                    reason = f"Slot already holds aliquot #{holder[1]} of '{holder[2]}' in Krill"
                                else:
                                    reason = f"Another row in this file already uses this slot (for '{holder[1]}')"
                                slot_conflicts.append({
                                    'box': box_name, 'row': row_pos, 'column': col_pos,
                                    'cell_line': sample_name, 'reason': reason,
                                    'existing_sample': holder[2] if holder[0] == 'existing' else None,
                                })
                                continue
                            occupied_slots[slot] = ('file', sample_name)
                            fixtures.append({
                                'model': 'sample.aliquotlocation',
                                'pk': pk_counter['location'],
                                'fields': {
                                    'aliquot': first_aliquot_pk,
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
                        print(f"Warning: Could not create location for aliquot {first_aliquot_pk}: {e}")

        # New boxes are 9x9 unless a tube sits beyond that; existing boxes are left as they are.
        for fixture in fixtures:
            if fixture['model'] == 'storage.box' and fixture['pk'] in box_extent:
                rows, columns = box_extent[fixture['pk']]
                fixture['fields']['rows'] = max(DEFAULT_BOX_SIZE, rows)
                fixture['fields']['columns'] = max(DEFAULT_BOX_SIZE, columns)

        if slot_conflicts:
            raise ImportConflictError(self._conflict_summary(slot_conflicts), slot_conflicts)

        self.reused_counts = {name: len(keys) for name, keys in reused.items()}
        return fixtures


@login_required
@require_minimum_role('lab_manager')
def download_import_refusals(request, token):
    """Download the full list of items a refused import could not use (CSV)."""
    import re
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise Http404
    path = os.path.join(get_upload_temp_dir(), f'imports_{request.user.id}', f'refused_{token}.csv')
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, 'rb'), as_attachment=True, filename='refused-import-rows.csv', content_type='text/csv')


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
    users = UserRole.objects.select_related('user').order_by('user__username')
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
    permissions = Permission.objects.select_related('user', 'content_type', 'granted_by').order_by('user__username', 'permission_type')
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
@require_minimum_role('lab_manager')
def audit_log(request):
    """View user audit logs"""
    form = AuditLogFilterForm(request.GET)
    logs = UserAuditLog.objects.select_related('user').order_by('-timestamp')
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


@login_required
def change_password(request):
    """Allow users to change their password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Change the password
            form.save()

            # Update the user's session to keep them logged in
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)

            # Log the password change
            UserAuditLog.log_action(
                user=request.user,
                action='password_changed',
                target_type='User',
                target_id=request.user.id,
                target_name=request.user.username,
                details={
                    'changed_by': request.user.username,
                    'ip_address': UserAuditLog.get_client_ip(request)
                },
                request=request
            )

            messages.success(request, 'Your password has been changed successfully.')
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)

    context = {
        'form': form,
        'title': 'Change Password',
    }
    return render(request, 'person/change_password.html', context)
