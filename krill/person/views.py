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

User = get_user_model()
from .models import UserPreference, UserRole, Permission, UserAuditLog
from .forms import (
    UserRoleForm, PermissionForm, UserPreferenceForm, 
    BulkPermissionForm, UserSearchForm, AuditLogFilterForm, CreateUserForm
)
from .decorators import require_permission, require_minimum_role, grant_object_permission, revoke_object_permission


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
