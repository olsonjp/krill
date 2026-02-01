from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.views import View
from .models import UserRole, Permission, UserAuditLog


def require_permission(permission, model_class=None, object_id_param='pk'):
    """
    Decorator to require a specific permission for a view.
    Args:
        permission (str): The permission to check (e.g., 'sample.create')
        model_class: Optional model class for object-level permissions
        object_id_param (str): URL parameter name for object ID
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user has role-based permission
            user_role = UserRole.get_or_create_for_user(request.user)
            if not user_role.has_permission(permission):
                # Log the denied access attempt
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    target_type=permission.split('.')[0] if '.' in permission else None,
                    details={'permission_denied': permission, 'reason': 'insufficient_role_permissions'},
                    request=request
                )
                return HttpResponseForbidden("Insufficient permissions")

            # Check object-level permissions if model_class is provided
            if model_class and object_id_param in kwargs:
                object_id = kwargs[object_id_param]
                if not has_object_permission(request.user, model_class, object_id, permission.split('.')[-1]):
                    UserAuditLog.log_action(
                        user=request.user,
                        action='view',
                        target_type=model_class.__name__ if model_class else None,
                        target_id=object_id,
                        details={'permission_denied': permission, 'reason': 'insufficient_object_permissions'},
                        request=request
                    )
                    return HttpResponseForbidden("Insufficient permissions for this object")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(role):
    """
    Decorator to require a specific role for a view.
    Args:
        role (str): The role to check (e.g., 'lab_admin', 'lab_manager')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = UserRole.get_or_create_for_user(request.user)
            if user_role.role != role:
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    details={'role_denied': role, 'current_role': user_role.role},
                    request=request
                )
                return HttpResponseForbidden("Insufficient role privileges")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_minimum_role(minimum_role):
    """
    Decorator to require a minimum role level for a view.
    Role hierarchy: viewer < lab_member < lab_manager < lab_admin
    Args:
        minimum_role (str): The minimum role required
    """
    role_hierarchy = {
        'viewer': 0,
        'lab_member': 1,
        'lab_manager': 2,
        'lab_admin': 3,
    }
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")

            user_role = UserRole.get_or_create_for_user(request.user)
            user_role_level = role_hierarchy.get(user_role.role, 0)
            required_level = role_hierarchy.get(minimum_role, 0)
            if user_role_level < required_level:
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    details={'minimum_role_denied': minimum_role, 'current_role': user_role.role},
                    request=request
                )
                return HttpResponseForbidden("Insufficient role privileges")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_access_level(level):
    """
    Decorator to check user has required access level for an object.
    Args:
        level (str): The access level required ('admins_only', 'admins_managers', 'all_members')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = UserRole.get_or_create_for_user(request.user)
            if not user_role.has_access_level(level):
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    details={'access_level_denied': level, 'current_role': user_role.role},
                    request=request
                )
                return HttpResponseForbidden("Insufficient access level")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def has_object_permission(user, model_class, object_id, permission_type):
    """
    Check if user has specific permission for a model instance.
    Args:
        user: The user to check
        model_class: The model class
        object_id: The object ID
        permission_type: The type of permission (view, edit, delete, etc.)
    Returns:
        bool: True if user has permission, False otherwise
    """
    # First check role-based permissions
    if not hasattr(user, 'role'):
        # Create default role if none exists
        from .models import UserRole
        if user.is_superuser:
            role = 'lab_admin'
        elif user.is_staff:
            role = 'lab_manager'
        else:
            role = 'viewer'
        UserRole.objects.create(
            user=user,
            role=role,
            department='',
            lab_unit=''
        )

    # Get the model name for permission checking
    model_name = model_class.__name__.lower()
    role_permission = f"{model_name}.{permission_type}"
    if not user.role.has_permission(role_permission):
        return False

    # Check for specific object-level permissions
    content_type = ContentType.objects.get_for_model(model_class)
    try:
        permission = Permission.objects.get(
            user=user,
            permission_type=permission_type,
            content_type=content_type,
            object_id=object_id
        )
        return permission.is_valid()
    except Permission.DoesNotExist:
        # No specific object permission, rely on role-based permission
        return True


def has_object_access(user, model_class, object_id):
    """
    Check if user has access to a specific object based on its access level.
    Args:
        user: The user to check
        model_class: The model class
        object_id: The object ID
    Returns:
        bool: True if user has access, False otherwise
    """
    try:
        obj = model_class.objects.get(id=object_id)
        user_role = UserRole.get_or_create_for_user(user)
        return user_role.can_access_object(obj)
    except model_class.DoesNotExist:
        return False


def grant_object_permission(user, model_class, object_id, permission_type, granted_by=None, expires_at=None):
    """
    Grant a specific permission to a user for a model instance.
    Args:
        user: The user to grant permission to
        model_class: The model class
        object_id: The object ID
        permission_type: The type of permission
        granted_by: The user granting the permission
        expires_at: Optional expiration date
    Returns:
        Permission: The created permission object
    """
    content_type = ContentType.objects.get_for_model(model_class)
    permission, created = Permission.objects.get_or_create(
        user=user,
        permission_type=permission_type,
        content_type=content_type,
        object_id=object_id,
        defaults={
            'granted_by': granted_by,
            'expires_at': expires_at
        }
    )
    if not created:
        # Update existing permission
        permission.granted_by = granted_by
        permission.expires_at = expires_at
        permission.save()

    # Log the permission grant
    UserAuditLog.log_action(
        user=granted_by or user,
        action='permission_granted',
        target_type=model_class.__name__,
        target_id=object_id,
        details={
            'granted_to': user.username,
            'permission_type': permission_type,
            'expires_at': expires_at.isoformat() if expires_at else None
        }
    )
    return permission


def revoke_object_permission(user, model_class, object_id, permission_type, revoked_by=None):
    """
    Revoke a specific permission from a user for a model instance.
    Args:
        user: The user to revoke permission from
        model_class: The model class
        object_id: The object ID
        permission_type: The type of permission
        revoked_by: The user revoking the permission
    Returns:
        bool: True if permission was revoked, False if it didn't exist
    """
    content_type = ContentType.objects.get_for_model(model_class)
    try:
        permission = Permission.objects.get(
            user=user,
            permission_type=permission_type,
            content_type=content_type,
            object_id=object_id
        )
        permission.delete()

        # Log the permission revocation
        UserAuditLog.log_action(
            user=revoked_by or user,
            action='permission_revoked',
            target_type=model_class.__name__ if model_class else None,
            target_id=object_id,
            details={
                'revoked_from': user.username,
                'permission_type': permission_type
            }
        )
        return True
    except Permission.DoesNotExist:
        return False


# Class-based view decorators
def require_permission_cbv(permission, model_class=None, object_id_param='pk'):
    """Class-based view version of require_permission decorator"""
    def decorator(cls):
        if not issubclass(cls, View):
            raise ValueError("Decorator can only be applied to View subclasses")
        original_dispatch = cls.dispatch
        @wraps(original_dispatch)
        def dispatch(self, request, *args, **kwargs):
            # Check if user has role-based permission
            user_role = UserRole.get_or_create_for_user(request.user)
            if not user_role.has_permission(permission):
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    target_type=permission.split('.')[0] if '.' in permission else None,
                    details={'permission_denied': permission, 'reason': 'insufficient_role_permissions'},
                    request=request
                )
                return HttpResponseForbidden("Insufficient permissions")

            # Check object-level permissions if model_class is provided
            if model_class and object_id_param in kwargs:
                object_id = kwargs[object_id_param]
                if not has_object_permission(request.user, model_class, object_id, permission.split('.')[-1]):
                    UserAuditLog.log_action(
                        user=request.user,
                        action='view',
                        target_type=model_class.__name__ if model_class else None,
                        target_id=object_id,
                        details={'permission_denied': permission, 'reason': 'insufficient_object_permissions'},
                        request=request
                    )
                    return HttpResponseForbidden("Insufficient permissions for this object")

            return original_dispatch(self, request, *args, **kwargs)
        cls.dispatch = dispatch
        return cls
    return decorator


def require_role_cbv(role):
    """Class-based view version of require_role decorator"""
    def decorator(cls):
        if not issubclass(cls, View):
            raise ValueError("Decorator can only be applied to View subclasses")
        original_dispatch = cls.dispatch
        @wraps(original_dispatch)
        def dispatch(self, request, *args, **kwargs):
            user_role = UserRole.get_or_create_for_user(request.user)
            if user_role.role != role:
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    details={'role_denied': role, 'current_role': user_role.role},
                    request=request
                )
                return HttpResponseForbidden("Insufficient role privileges")
            return original_dispatch(self, request, *args, **kwargs)
        cls.dispatch = dispatch
        return cls
    return decorator


def require_access_level_cbv(level):
    """Class-based view version of require_access_level decorator"""
    def decorator(cls):
        if not issubclass(cls, View):
            raise ValueError("Decorator can only be applied to View subclasses")
        original_dispatch = cls.dispatch
        @wraps(original_dispatch)
        def dispatch(self, request, *args, **kwargs):
            user_role = UserRole.get_or_create_for_user(request.user)
            if not user_role.has_access_level(level):
                UserAuditLog.log_action(
                    user=request.user,
                    action='view',
                    details={'access_level_denied': level, 'current_role': user_role.role},
                    request=request
                )
                return HttpResponseForbidden("Insufficient access level")
            return original_dispatch(self, request, *args, **kwargs)
        cls.dispatch = dispatch
        return cls
    return decorator
