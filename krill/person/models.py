from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class User(AbstractUser):
    pass


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    dark_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"


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
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create a UserRole for a user"""
        try:
            return user.role
        except UserRole.DoesNotExist:
            if user.is_superuser:
                role = 'lab_admin'
            elif user.is_staff:
                role = 'lab_manager'
            else:
                role = 'viewer'
            return cls.objects.create(
                user=user,
                role=role,
                department='',
                lab_unit=''
            )
    
    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def has_permission(self, permission):
        """Check if user has a specific permission based on their role"""
        role_permissions = self.get_role_permissions()
        return permission in role_permissions
    
    def get_role_permissions(self):
        """Get permissions based on role hierarchy"""
        permissions = {
            'lab_admin': [
                # Sample permissions
                'sample.view', 'sample.create', 'sample.edit', 'sample.delete',
                'sample.approve', 'sample.bulk_operations',
                # Aliquot permissions
                'aliquot.view', 'aliquot.create', 'aliquot.edit', 'aliquot.delete',
                'aliquot.split', 'aliquot.merge', 'aliquot.store',
                # Storage permissions
                'storage.view', 'storage.create', 'storage.edit', 'storage.delete',
                'storage.manage_capacity', 'storage.monitor',
                # User management
                'user.view', 'user.create', 'user.edit', 'user.delete',
                'user.assign_roles', 'user.manage_permissions',
                # System permissions
                'system.admin', 'system.reports', 'system.audit_logs',
                'system.settings', 'system.backup',
            ],
            'lab_manager': [
                # Sample permissions
                'sample.view', 'sample.create', 'sample.edit', 'sample.delete',
                'sample.approve', 'sample.bulk_operations',
                # Aliquot permissions
                'aliquot.view', 'aliquot.create', 'aliquot.edit', 'aliquot.delete',
                'aliquot.split', 'aliquot.merge', 'aliquot.store',
                # Storage permissions
                'storage.view', 'storage.create', 'storage.edit', 'storage.delete',
                'storage.manage_capacity', 'storage.monitor',
                # Limited user management
                'user.view', 'user.create', 'user.edit',
                # System permissions
                'system.reports', 'system.audit_logs',
            ],
            'lab_member': [
                # Sample permissions
                'sample.view', 'sample.create', 'sample.edit',
                # Aliquot permissions
                'aliquot.view', 'aliquot.create', 'aliquot.edit',
                'aliquot.split', 'aliquot.store',
                # Storage permissions
                'storage.view', 'storage.create', 'storage.edit',
                # Limited system access
                'system.reports',
            ],
            'viewer': [
                # Read-only permissions
                'sample.view', 'aliquot.view', 'storage.view',
            ]
        }
        return permissions.get(self.role, [])
    
    def has_access_level(self, object_access_level):
        """
        Check if user has access to an object based on its access level restriction.
        
        Args:
            object_access_level (str): The access level of the object ('admins_only', 'admins_managers', 'all_members')
        
        Returns:
            bool: True if user has access, False otherwise
        """
        # Define role hierarchy for access level checking
        role_hierarchy = {
            'lab_admin': 3,
            'lab_manager': 2,
            'lab_member': 1,
            'viewer': 0,
        }
        
        # Define access level requirements
        access_level_requirements = {
            'admins_only': 3,  # Only lab_admin
            'admins_managers': 2,  # lab_admin and lab_manager
            'all_members': 1,  # lab_admin, lab_manager, and lab_member
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_level = access_level_requirements.get(object_access_level, 0)
        
        return user_level >= required_level
    
    def can_access_object(self, obj):
        """
        Check if user can access a specific object based on its access level.
        
        Args:
            obj: Model instance with access_level field
        
        Returns:
            bool: True if user has access, False otherwise
        """
        if not hasattr(obj, 'access_level'):
            # If object doesn't have access_level, allow access
            return True
        
        return self.has_access_level(obj.access_level)


class Permission(models.Model):
    """Granular permissions for specific model instances"""
    PERMISSION_TYPES = [
        ('view', 'View'),
        ('create', 'Create'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('bulk_operations', 'Bulk Operations'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions')
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='object_permissions')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'permission_type', 'content_type', 'object_id']
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
    
    def __str__(self):
        return f"{self.user.username} - {self.permission_type} - {self.content_object}"
    
    def is_valid(self):
        """Check if permission is still valid (not expired)"""
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True


class UserAuditLog(models.Model):
    """Audit trail for user actions"""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('permission_granted', 'Permission Granted'),
        ('permission_revoked', 'Permission Revoked'),
        ('role_changed', 'Role Changed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.IntegerField(null=True, blank=True)
    target_name = models.CharField(max_length=200, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "User Audit Log"
        verbose_name_plural = "User Audit Logs"
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, user, action, target_type=None, target_id=None, target_name=None, 
                   details=None, request=None):
        """Convenience method to log user actions"""
        if details is None:
            details = {}
        ip_address = None
        user_agent = ""
        if request:
            ip_address = cls.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        return cls.objects.create(
            user=user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip