# TODO: Missing Server-Side Functionality

This document tracks frontend functionality that exists but lacks proper server-side implementation.

## 🔴 Critical Issues (Breaking Functionality)

### 1. Database Migration Issue - Missing `deleted` Column
**Status**: ✅ COMPLETED & TESTED  
**Issue**: `no such column: sample_aliquot.deleted`  
**Impact**: Cannot create test data, potential runtime errors  
**Root Cause**: Migration issue with Aliquot model's `deleted` field  

**Fix Applied**:
```python
# Updated Aliquot model in sample/models/aliquot.py
from django.utils import timezone

class Aliquot(models.Model):
    # ... existing fields ...
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
```

**Migration Created**: `0003_add_aliquot_timestamp_fields.py`
- Added `deleted` field with default=False
- Added `deleted_at` field (nullable)
- Added `created_at` field with default=timezone.now
- Added `updated_at` field with default=timezone.now

**Test Results**:
- ✅ Can successfully create test aliquots
- ✅ All timestamp fields work correctly
- ✅ No database errors when accessing aliquot data
- ✅ Storage capacity testing can now proceed with sample data

### 2. Storage Capacity Endpoint
**Status**: ✅ COMPLETED & TESTED  
**Frontend**: `dashboard.js` makes fetch request to `/storage/capacity/`  
**Backend**: View exists in `storage/views/capacity.py` and now registered in URLs  
**Impact**: Dashboard storage usage calculation now works  

**Fix Applied**:
```python
# Added to storage/urls.py
from .views.capacity import box_capacity
path('capacity/', box_capacity, name='capacity'),
```

**Test Results**:
- ✅ Endpoint returns 200 status code for authenticated users
- ✅ Endpoint returns 302 redirect for unauthenticated users (login required)
- ✅ Returns correct JSON structure: `{"sites": {}, "total_slots": 0, "used_slots": 0, "free_slots": 0}`
- ✅ Frontend JavaScript can properly parse the response and calculate percentages
- ✅ Handles empty database gracefully
- ✅ Correctly calculates capacity with test data (96 total slots, 0 used)

---

## 🟡 Missing Features (Non-breaking but incomplete)

### 2. Server-Side Search API
**Status**: ❌ No implementation  
**Frontend**: Client-side search in `sample/list.html` and `storage/list.html`  
**Current**: JavaScript filters DOM elements  
**Need**: API endpoints for efficient server-side search  

**Required Endpoints**:
- `GET /samples/search/?q=<query>&type=<model_type>`
- `GET /storage/search/?q=<query>&type=<model_type>`

**Implementation**:
```python
# Add to sample/views/
@login_required
def search_samples(request):
    query = request.GET.get('q', '')
    model_type = request.GET.get('type', 'sample')
    # Implement search logic
    return JsonResponse({'results': results})
```

### 3. Server-Side Sorting API
**Status**: ❌ No implementation  
**Frontend**: Client-side sorting in list templates  
**Current**: JavaScript sorts DOM elements  
**Need**: API endpoints for server-side sorting  

**Required Endpoints**:
- `GET /samples/?sort=<field>&order=<asc|desc>`
- `GET /storage/?sort=<field>&order=<asc|desc>`

### 4. Activity Feed API
**Status**: ❌ No implementation  
**Frontend**: Static activity items in `home.html`  
**Current**: Hardcoded activity examples  
**Need**: Real-time activity tracking and API  

**Required Endpoints**:
- `GET /activity/recent/` - Recent user activities
- `POST /activity/log/` - Log new activity

**Implementation**:
```python
# New app: activity/
class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

### 5. Dashboard Statistics API
**Status**: ❌ No implementation  
**Frontend**: Hardcoded stats in `home.html`  
**Current**: Static numbers (248 samples, 78% usage, etc.)  
**Need**: Dynamic statistics from database  

**Required Endpoints**:
- `GET /dashboard/stats/` - Overall system statistics
- `GET /dashboard/user-stats/` - User-specific statistics

**Implementation**:
```python
# Add to krill/views/
@login_required
def dashboard_stats(request):
    stats = {
        'active_samples': Sample.objects.filter(active=True).count(),
        'storage_usage': calculate_storage_percentage(),
        'recent_reports': Report.objects.filter(created_at__gte=timezone.now()-timedelta(days=7)).count(),
        'alerts': Alert.objects.filter(resolved=False).count(),
    }
    return JsonResponse(stats)
```

### 6. Quick Actions API
**Status**: ❌ No implementation  
**Frontend**: Action buttons in templates  
**Current**: Buttons exist but no functionality  
**Need**: Server-side handlers for quick actions  

**Required Endpoints**:
- `POST /samples/quick-create/` - Quick sample creation
- `GET /samples/find/` - Sample finder
- `POST /reports/generate/` - Quick report generation

### 7. Homepage Dashboard Statistics API
**Status**: ❌ No implementation  
**Frontend**: Hardcoded stats in `home.html`  
**Current**: Static numbers (248 samples, 78% usage, 15 reports, 2 alerts)  
**Need**: Dynamic statistics from database  

**Required Endpoints**:
- `GET /dashboard/stats/` - Overall system statistics

**Implementation**:
```python
# Add to krill/views/
@login_required
def dashboard_stats(request):
    stats = {
        'active_samples': Sample.objects.filter(deleted=False).count(),
        'storage_usage': calculate_storage_percentage(),
        'recent_reports': Report.objects.filter(created_at__gte=timezone.now()-timedelta(days=7)).count(),
        'alerts': Alert.objects.filter(resolved=False).count(),
    }
    return JsonResponse(stats)
```

### 8. Recent Activity Feed API
**Status**: ❌ No implementation  
**Frontend**: Static activity items in `home.html`  
**Current**: Hardcoded activity examples  
**Need**: Real-time activity tracking and API  

**Required Endpoints**:
- `GET /activity/recent/` - Recent user activities
- `POST /activity/log/` - Log new activity

**Implementation**:
```python
# New app: activity/
class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)  # 'create', 'update', 'delete'
    target_type = models.CharField(max_length=50)  # 'sample', 'storage', 'report'
    target_id = models.IntegerField()
    target_name = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)
```

### 9. Storage Management Dashboard API
**Status**: ❌ No implementation  
**Frontend**: Hardcoded stats in `storage/storage.html`  
**Current**: Static numbers (4 freezers, 156/200 boxes, 1,248 samples)  
**Need**: Dynamic storage statistics  

**Required Endpoints**:
- `GET /storage/dashboard/` - Storage overview statistics
- `GET /storage/freezers/` - Freezer status and capacity

**Implementation**:
```python
@login_required
def storage_dashboard(request):
    stats = {
        'active_freezers': Device.objects.count(),
        'total_boxes': Box.objects.count(),
        'available_boxes': Box.objects.filter(aliquotlocation__isnull=True).count(),
        'total_samples': AliquotLocation.objects.count(),
        'freezer_status': get_freezer_status(),
    }
    return JsonResponse(stats)
```

### 10. Freezer Status Monitoring API
**Status**: ❌ No implementation  
**Frontend**: Freezer units with temperature and capacity in `storage/storage.html`  
**Current**: Static freezer data (Freezer A-D with hardcoded temps and capacities)  
**Need**: Real freezer monitoring system  

**Required Endpoints**:
- `GET /storage/freezers/status/` - Real-time freezer status
- `GET /storage/freezers/<id>/contents/` - Freezer contents

**Implementation**:
```python
class FreezerStatus(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=[
        ('operational', 'Operational'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ])
```

### 11. Sample Search and Find API
**Status**: ❌ No implementation  
**Frontend**: "Find Sample" buttons in multiple templates  
**Current**: No search functionality  
**Need**: Comprehensive sample search system  

**Required Endpoints**:
- `GET /samples/search/?q=<query>` - Search samples by name, ID, or location
- `GET /samples/find/` - Advanced sample finder interface

### 12. Report Generation API
**Status**: ❌ No implementation  
**Frontend**: "Generate Report" buttons in templates  
**Current**: No report generation functionality  
**Need**: Automated report generation system  

**Required Endpoints**:
- `POST /reports/generate/` - Generate new report
- `GET /reports/list/` - List available reports
- `GET /reports/<id>/download/` - Download generated report

### 13. Alert System API
**Status**: ❌ No implementation  
**Frontend**: Alert indicators in `home.html`  
**Current**: Static alert count (2 New)  
**Need**: Real-time alert system  

**Required Endpoints**:
- `GET /alerts/list/` - List active alerts
- `POST /alerts/create/` - Create new alert
- `POST /alerts/<id>/resolve/` - Resolve alert

**Implementation**:
```python
class Alert(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
```

### 14. Issue Reporting API
**Status**: ❌ No implementation  
**Frontend**: "Report Issue" button in `storage/storage.html`  
**Current**: No issue reporting functionality  
**Need**: Issue tracking system  

**Required Endpoints**:
- `POST /issues/report/` - Report new issue
- `GET /issues/list/` - List reported issues
- `POST /issues/<id>/update/` - Update issue status

### 15. Data Entry Form Styling Improvements
**Status**: ❌ Needs improvement  
**Frontend**: Basic form styling exists but needs enhancement  
**Current**: Simple forms with basic styling in `forms/model_form.html` and inline styles  
**Need**: Modern, user-friendly form design with better UX  

**Issues to Address**:
- Inconsistent form styling across different templates
- Basic input styling without modern design elements
- Missing form validation visual feedback
- No responsive design considerations
- Limited accessibility features
- Inconsistent button styling between create/edit forms

**Required Improvements**:
- Modern form input styling with focus states
- Better form layout and spacing
- Enhanced validation error display
- Responsive form design
- Improved accessibility (ARIA labels, keyboard navigation)
- Consistent button styling across all forms
- Better form field grouping and organization
- Enhanced help text styling

**Implementation**:
```css
/* Enhanced form styling */
.form-container {
    max-width: 800px;
    margin: 0 auto;
    background: var(--color-white);
    padding: 2.5rem;
    border-radius: 15px;
    box-shadow: var(--box-shadow);
}

.form-field {
    margin-bottom: 1.5rem;
    position: relative;
}

.form-field label {
    display: block;
    font-weight: 600;
    color: var(--color-dark);
    margin-bottom: 0.5rem;
    font-size: 0.95rem;
}

.form-field input,
.form-field select,
.form-field textarea {
    width: 100%;
    padding: 1rem;
    border: 2px solid var(--color-light);
    border-radius: 8px;
    font-size: 1rem;
    transition: all 0.3s ease;
    background: var(--color-white);
}

.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(108, 155, 207, 0.1);
}

.form-field.error input,
.form-field.error select,
.form-field.error textarea {
    border-color: var(--color-danger);
}

.field-errors {
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: rgba(255, 0, 96, 0.1);
    border-radius: 5px;
    border-left: 3px solid var(--color-danger);
}

.help-text {
    margin-top: 0.5rem;
    font-size: 0.85rem;
    color: var(--color-info-dark);
    font-style: italic;
}

.form-actions {
    display: flex;
    gap: 1rem;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--color-light);
}

.submit-btn,
.cancel-btn {
    padding: 0.8rem 1.5rem;
    border-radius: 8px;
    font-weight: 500;
    font-size: 1rem;
    transition: all 0.3s ease;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.submit-btn {
    background: var(--color-primary);
    color: white;
    border: none;
}

.submit-btn:hover {
    background: var(--color-primary-variant);
    transform: translateY(-1px);
}

.cancel-btn {
    background: var(--color-light);
    color: var(--color-dark);
    border: 1px solid var(--color-light);
}

.cancel-btn:hover {
    background: var(--color-white);
    border-color: var(--color-dark);
}
```

**Priority**: High - Critical for user experience

### 16. Aliquot Management API
**Status**: ❌ No implementation  
**Frontend**: Missing buttons for aliquot operations in detail views  
**Current**: Basic CRUD for aliquots exists, but missing specialized operations  
**Need**: Advanced aliquot management functionality  

**Required Endpoints**:
- `POST /samples/<id>/create-aliquot/` - Create new aliquot from sample
- `POST /aliquots/<id>/create-child/` - Create child aliquot (derivative)
- `POST /aliquots/<id>/store/` - Store aliquot in specific location
- `POST /aliquots/<id>/split/` - Split aliquot into multiple aliquots
- `POST /aliquots/<id>/merge/` - Merge aliquots
- `GET /aliquots/<id>/children/` - Get child aliquots
- `GET /aliquots/<id>/history/` - Get aliquot history/lineage

**Implementation**:
```python
# Add to sample/views/
@login_required
def create_aliquot_from_sample(request, sample_id):
    """Create a new aliquot from an existing sample"""
    sample = get_object_or_404(Sample, id=sample_id)
    if request.method == 'POST':
        form = AliquotForm(request.POST)
        if form.is_valid():
            aliquot = form.save(commit=False)
            aliquot.sample = sample
            aliquot.save()
            return JsonResponse({'success': True, 'aliquot_id': aliquot.id})
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def create_child_aliquot(request, aliquot_id):
    """Create a child aliquot from parent aliquot"""
    parent = get_object_or_404(Aliquot, id=aliquot_id)
    if request.method == 'POST':
        form = AliquotForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = parent
            child.sample = parent.sample
            child.save()
            return JsonResponse({'success': True, 'aliquot_id': child.id})
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def store_aliquot(request, aliquot_id):
    """Store aliquot in specific storage location"""
    aliquot = get_object_or_404(Aliquot, id=aliquot_id)
    if request.method == 'POST':
        form = AliquotLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.aliquot = aliquot
            location.save()
            return JsonResponse({'success': True, 'location_id': location.id})
    return JsonResponse({'success': False, 'errors': form.errors})
```

### 17. Aliquot Management UI Components
**Status**: ❌ No implementation  
**Frontend**: Missing UI buttons and forms for aliquot operations  
**Current**: Basic detail view exists, but no action buttons  
**Need**: Interactive UI for aliquot management  

**Required UI Components**:
- "Create Aliquot" button on sample detail pages
- "Create Child Aliquot" button on aliquot detail pages
- "Store Aliquot" button with location selector
- "Split Aliquot" form with quantity distribution
- "Merge Aliquots" interface
- Aliquot lineage/history display
- Storage location assignment interface

**Implementation**:
```html
<!-- Add to sample/detail.html for samples -->
<div class="action-buttons">
    <button class="action-btn" onclick="createAliquot({{ object.id }})">
        <span class="material-icons-round">add_circle</span>
        Create Aliquot
    </button>
    <button class="action-btn" onclick="viewAliquots({{ object.id }})">
        <span class="material-icons-round">list</span>
        View Aliquots
    </button>
</div>

<!-- Add to sample/detail.html for aliquots -->
<div class="action-buttons">
    <button class="action-btn" onclick="createChildAliquot({{ object.id }})">
        <span class="material-icons-round">call_split</span>
        Create Child Aliquot
    </button>
    <button class="action-btn" onclick="storeAliquot({{ object.id }})">
        <span class="material-icons-round">inventory_2</span>
        Store Aliquot
    </button>
    <button class="action-btn" onclick="splitAliquot({{ object.id }})">
        <span class="material-icons-round">content_cut</span>
        Split Aliquot
    </button>
</div>
```



## 🟢 Enhancement Opportunities

### 18. Real-time Updates
**Status**: ❌ No implementation  
**Frontend**: Static data that requires page refresh  
**Need**: WebSocket or Server-Sent Events for real-time updates  

### 19. Bulk Operations
**Status**: ❌ No implementation  
**Frontend**: Individual item operations only  
**Need**: Bulk delete, bulk update, bulk export  

### 20. Export Functionality
**Status**: ❌ No implementation  
**Frontend**: No export buttons  
**Need**: CSV, Excel, PDF export APIs

### 21. Aliquot Management API
**Status**: ❌ No implementation  
**Frontend**: Missing buttons for aliquot operations in detail views  
**Current**: Basic CRUD for aliquots exists, but missing specialized operations  
**Need**: Advanced aliquot management functionality  

**Required Endpoints**:
- `POST /samples/<id>/create-aliquot/` - Create new aliquot from sample
- `POST /aliquots/<id>/create-child/` - Create child aliquot (derivative)
- `POST /aliquots/<id>/store/` - Store aliquot in specific location
- `POST /aliquots/<id>/split/` - Split aliquot into multiple aliquots
- `POST /aliquots/<id>/merge/` - Merge aliquots
- `GET /aliquots/<id>/children/` - Get child aliquots
- `GET /aliquots/<id>/history/` - Get aliquot history/lineage

**Implementation**:
```python
# Add to sample/views/
@login_required
def create_aliquot_from_sample(request, sample_id):
    """Create a new aliquot from an existing sample"""
    sample = get_object_or_404(Sample, id=sample_id)
    if request.method == 'POST':
        form = AliquotForm(request.POST)
        if form.is_valid():
            aliquot = form.save(commit=False)
            aliquot.sample = sample
            aliquot.save()
            return JsonResponse({'success': True, 'aliquot_id': aliquot.id})
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def create_child_aliquot(request, aliquot_id):
    """Create a child aliquot from parent aliquot"""
    parent = get_object_or_404(Aliquot, id=aliquot_id)
    if request.method == 'POST':
        form = AliquotForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = parent
            child.sample = parent.sample
            child.save()
            return JsonResponse({'success': True, 'aliquot_id': child.id})
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def store_aliquot(request, aliquot_id):
    """Store aliquot in specific storage location"""
    aliquot = get_object_or_404(Aliquot, id=aliquot_id)
    if request.method == 'POST':
        form = AliquotLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.aliquot = aliquot
            location.save()
            return JsonResponse({'success': True, 'location_id': location.id})
    return JsonResponse({'success': False, 'errors': form.errors})
```

### 22. Aliquot Management UI Components
**Status**: ❌ No implementation  
**Frontend**: Missing UI buttons and forms for aliquot operations  
**Current**: Basic detail view exists, but no action buttons  
**Need**: Interactive UI for aliquot management  

**Required UI Components**:
- "Create Aliquot" button on sample detail pages
- "Create Child Aliquot" button on aliquot detail pages
- "Store Aliquot" button with location selector
- "Split Aliquot" form with quantity distribution
- "Merge Aliquots" interface
- Aliquot lineage/history display
- Storage location assignment interface

**Implementation**:
```html
<!-- Add to sample/detail.html for samples -->
<div class="action-buttons">
    <button class="action-btn" onclick="createAliquot({{ object.id }})">
        <span class="material-icons-round">add_circle</span>
        Create Aliquot
    </button>
    <button class="action-btn" onclick="viewAliquots({{ object.id }})">
        <span class="material-icons-round">list</span>
        View Aliquots
    </button>
</div>

<!-- Add to sample/detail.html for aliquots -->
<div class="action-buttons">
    <button class="action-btn" onclick="createChildAliquot({{ object.id }})">
        <span class="material-icons-round">call_split</span>
        Create Child Aliquot
    </button>
    <button class="action-btn" onclick="storeAliquot({{ object.id }})">
        <span class="material-icons-round">inventory_2</span>
        Store Aliquot
    </button>
    <button class="action-btn" onclick="splitAliquot({{ object.id }})">
        <span class="material-icons-round">content_cut</span>
        Split Aliquot
    </button>
</div>
```  

### 23. User Permissions and Role Management
**Status**: ✅ COMPLETED & IMPLEMENTED  
**Current**: Comprehensive role-based access control system with Django integration  
**Implementation**: Full role-based permission system with audit logging  

**✅ Issues Addressed**:
- ✅ Role-based permissions implemented (Lab Admin, Manager, Member, Viewer)
- ✅ Granular permissions for different operations
- ✅ User groups and organizational structure (departments, lab units)
- ✅ Complete audit trail for user actions
- ✅ Permission-based UI components and navigation

**✅ Features Implemented**:
- ✅ Role-based access control (Lab Admin, Lab Manager, Lab Member, Viewer)
- ✅ Granular permissions for CRUD operations across all models
- ✅ User groups and organizational units (departments, lab units)
- ✅ Permission-based UI components and navigation
- ✅ Comprehensive audit logging for user actions
- ✅ Complete user management interface

**✅ Implementation Details**:

**Models Created**:
```python
# person/models.py
class UserRole(models.Model):
    ROLE_CHOICES = [
        ('lab_admin', 'Lab Administrator'),
        ('lab_manager', 'Lab Manager'),
        ('lab_member', 'Lab Member'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.CharField(max_length=100, blank=True, null=True)
    lab_unit = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def has_permission(self, permission):
        """Check if user has a specific permission based on their role"""
        role_permissions = self.get_role_permissions()
        return permission in role_permissions

class Permission(models.Model):
    """Granular permissions for specific model instances"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions')
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='object_permissions')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

class UserAuditLog(models.Model):
    """Audit trail for user actions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.IntegerField(null=True, blank=True)
    target_name = models.CharField(max_length=200, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
```

**Permission Decorators Implemented**:
```python
# person/decorators.py
@require_permission('sample.create')
def create_sample(request):
    # Only users with 'sample.create' permission can access
    pass

@require_minimum_role('lab_manager')
def manage_users(request):
    # Only lab managers and admins can access
    pass

@require_role('lab_admin')
def system_admin(request):
    # Only lab admins can access
    pass
```

**✅ Endpoints Implemented**:
- ✅ `GET /users/` - List all users with roles and permissions
- ✅ `GET /users/create/` - Create new user form
- ✅ `GET /users/<id>/` - View user details and permissions
- ✅ `GET /users/<id>/edit/` - Edit user role and organization
- ✅ `GET /users/audit-logs/` - View comprehensive audit log
- ✅ `GET /users/permissions/` - List object-level permissions
- ✅ `POST /users/permissions/grant/` - Grant object-level permissions
- ✅ `POST /users/permissions/revoke/` - Revoke object-level permissions

**✅ UI Components Implemented**:
- ✅ User management interface with search and filtering
- ✅ Role assignment forms with role information
- ✅ Permission-based button visibility and navigation
- ✅ Comprehensive audit log viewer with filtering
- ✅ User profile with role information and permissions
- ✅ Create user form with role selection
- ✅ User role editing interface

**✅ Django Integration**:
- ✅ Automatic UserRole creation for new users
- ✅ Django superuser → Lab Administrator role mapping
- ✅ Staff users → Lab Manager role mapping
- ✅ Signals for automatic role management
- ✅ Management command for existing user setup
- ✅ Enhanced Django admin interface

**✅ Security Features**:
- ✅ Role hierarchy enforcement
- ✅ Object-level permissions
- ✅ Permission expiration
- ✅ Comprehensive audit logging
- ✅ IP address and user agent tracking
- ✅ Permission denial logging

**✅ Database Migrations**:
- ✅ All models properly migrated
- ✅ Nullable fields for optional data
- ✅ Proper foreign key relationships
- ✅ Indexes for performance

**Priority**: ✅ COMPLETED - Critical security and access control implemented

---

## 📋 Implementation Priority

1. **Critical Priority** (Fix database errors):
   - ✅ Database Migration Issue - Missing `deleted` Column (#1) - **COMPLETED**

2. **High Priority** (Fix breaking functionality):
   - ✅ Storage capacity endpoint URL registration - **COMPLETED**

3. **Medium Priority** (Improve user experience):
   - ✅ User Permissions and Role Management (#23) - **COMPLETED**
   - ✅ Data Entry Form Styling Improvements (#15) - **COMPLETED**
   - Homepage Dashboard Statistics API (#7)
   - Storage Management Dashboard API (#9)
   - Sample Search and Find API (#11)
   - Alert System API (#13)
   - Aliquot Management API (#21)

4. **Medium-Low Priority** (Enhance functionality):
   - Recent Activity Feed API (#8)
   - Freezer Status Monitoring API (#10)
   - Report Generation API (#12)
   - Issue Reporting API (#14)
   - Aliquot Management UI Components (#22)
   - Server-side search API (#2)
   - Server-side sorting API (#3)

5. **Low Priority** (Nice to have):
   - Quick actions API (#6)
   - Real-time updates (#18)
   - Bulk operations (#19)
   - Export functionality (#20)

**Next Recommended Items:**
- ✅ **User Permissions and Role Management (#23)** - **COMPLETED** - Critical for security and access control
- ✅ **Data Entry Form Styling Improvements (#15)** - **COMPLETED** - High impact for user experience
- **Homepage Dashboard Statistics API (#7)** - High impact for user experience
- **Sample Search and Find API (#11)** - Essential functionality for sample management
- **Alert System API (#13)** - Important for system monitoring

---

## 🛠️ Development Notes

- All new APIs should include proper authentication (`@login_required`)
- Use Django REST Framework for consistent API responses
- Implement proper error handling and validation
- Add appropriate tests for new functionality
- Consider pagination for list endpoints
- Use Django signals for activity tracking
- Consider caching for dashboard statistics

---

## 📝 Testing Checklist

For each implemented feature:
- [ ] Unit tests for models and views
- [ ] Integration tests for API endpoints
- [ ] Frontend integration testing
- [ ] Error handling validation
- [ ] Performance testing for large datasets
- [ ] Security testing (authentication, authorization)
