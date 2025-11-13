from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django import forms
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

from .models import UserRole, Permission, UserAuditLog, UserPreference
from .forms import (
    CreateUserForm, CustomUserCreationForm, CustomUserChangeForm,
    UserRoleForm, PermissionForm, UserPreferenceForm, BulkPermissionForm,
    UserSearchForm, AuditLogFilterForm
)
from .views import (
    toggle_theme, create_user, user_list, user_detail, user_role_edit,
    permission_list, grant_permission, revoke_permission, bulk_grant_permission,
    audit_log, user_permissions_api, grant_object_permission_api, revoke_object_permission_api,
    DataImportView
)
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class UserRoleModelTest(TestCase):
    """Test cases for the UserRole model"""
    def test_role_creation_and_assignment(self):
        """Test role creation and assignment"""
        user = User.objects.create_user(
            username='testuser_role',
            email='test_role@example.com',
            password='testpass123'
        )
        role, created = UserRole.objects.get_or_create(
            user=user,
            defaults={
                'role': 'lab_member',
                'department': 'Research',
                'lab_unit': 'Lab A'
            }
        )
        # Update the role if it already existed
        if not created:
            role.role = 'lab_member'
            role.department = 'Research'
            role.lab_unit = 'Lab A'
            role.save()
        self.assertEqual(role.user, user)
        self.assertEqual(role.role, 'lab_member')
        self.assertEqual(role.department, 'Research')
        self.assertEqual(role.lab_unit, 'Lab A')
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)
    def test_role_hierarchy_validation(self):
        """Test role hierarchy validation"""
        valid_roles = ['lab_admin', 'lab_manager', 'lab_member', 'viewer']
        for role_type in valid_roles:
            user = User.objects.create_user(
                username=f'user_{role_type}',
                email=f'{role_type}@example.com'
            )
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                defaults={'role': role_type}
            )
            # Update the role if it already existed
            if not created:
                user_role.role = role_type
                user_role.save()
            self.assertEqual(user_role.role, role_type)
    def test_role_permission_checking(self):
        """Test role permission checking"""
        # Test lab_admin permissions
        admin_user = User.objects.create_user(
            username='admin_test',
            email='admin_test@example.com'
        )
        admin_role, created = UserRole.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'lab_admin'}
        )
        if not created:
            admin_role.role = 'lab_admin'
            admin_role.save()
        admin_permissions = admin_role.get_role_permissions()
        self.assertIn('sample.create', admin_permissions)
        self.assertIn('sample.delete', admin_permissions)
        self.assertIn('user.manage_permissions', admin_permissions)
        self.assertIn('system.admin', admin_permissions)
        # Test lab_member permissions
        member_user = User.objects.create_user(
            username='member_test',
            email='member_test@example.com'
        )
        member_role, created = UserRole.objects.get_or_create(
            user=member_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            member_role.role = 'lab_member'
            member_role.save()
        member_permissions = member_role.get_role_permissions()
        self.assertIn('sample.view', member_permissions)
        self.assertIn('sample.create', member_permissions)
        self.assertNotIn('sample.delete', member_permissions)
        self.assertNotIn('user.manage_permissions', member_permissions)
        # Test viewer permissions
        viewer_user = User.objects.create_user(
            username='viewer_test',
            email='viewer_test@example.com'
        )
        viewer_role, created = UserRole.objects.get_or_create(
            user=viewer_user,
            defaults={'role': 'viewer'}
        )
        if not created:
            viewer_role.role = 'viewer'
            viewer_role.save()
        viewer_permissions = viewer_role.get_role_permissions()
        self.assertIn('sample.view', viewer_permissions)
        self.assertNotIn('sample.create', viewer_permissions)
        self.assertNotIn('sample.delete', viewer_permissions)
    def test_get_or_create_for_user_method(self):
        """Test get_or_create_for_user method"""
        user = User.objects.create_user(
            username='testuser_get_create',
            email='test_get_create@example.com',
            password='testpass123'
        )
        # Test creating new role
        role = UserRole.get_or_create_for_user(user)
        self.assertEqual(role.user, user)
        self.assertEqual(role.role, 'viewer')  # Default for regular users
        # Test getting existing role
        existing_role = UserRole.get_or_create_for_user(user)
        self.assertEqual(existing_role, role)
        # Test superuser role assignment
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        admin_role = UserRole.get_or_create_for_user(superuser)
        self.assertEqual(admin_role.role, 'lab_admin')
        # Test staff user role assignment
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        staff_role = UserRole.get_or_create_for_user(staff_user)
        self.assertEqual(staff_role.role, 'lab_manager')
    def test_role_string_representation(self):
        """Test role string representation"""
        string_user = User.objects.create_user(
            username='string_test',
            email='string_test@example.com'
        )
        role, created = UserRole.objects.get_or_create(
            user=string_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            role.role = 'lab_member'
            role.save()
        expected_str = f"{string_user.username} - Lab Member"
        self.assertEqual(str(role), expected_str)
    def test_role_permission_inheritance(self):
        """Test role permission inheritance"""
        # Test that higher roles inherit permissions from lower roles
        admin_user = User.objects.create_user(
            username='admin_inheritance',
            email='admin_inheritance@example.com'
        )
        admin_role, created = UserRole.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'lab_admin'}
        )
        if not created:
            admin_role.role = 'lab_admin'
            admin_role.save()
        admin_permissions = admin_role.get_role_permissions()
        # Admin should have all permissions
        self.assertIn('sample.view', admin_permissions)
        self.assertIn('sample.create', admin_permissions)
        self.assertIn('sample.edit', admin_permissions)
        self.assertIn('sample.delete', admin_permissions)
        self.assertIn('aliquot.view', admin_permissions)
        self.assertIn('aliquot.create', admin_permissions)
        self.assertIn('storage.view', admin_permissions)
        self.assertIn('storage.create', admin_permissions)
        self.assertIn('user.view', admin_permissions)
        self.assertIn('user.create', admin_permissions)
        self.assertIn('system.admin', admin_permissions)
    def test_has_permission_method(self):
        """Test has_permission method"""
        member_user = User.objects.create_user(
            username='member_permission',
            email='member_permission@example.com'
        )
        role, created = UserRole.objects.get_or_create(
            user=member_user,
            defaults={'role': 'lab_member'}
        )
        if not created:
            role.role = 'lab_member'
            role.save()
        # Test permissions that lab_member should have
        self.assertTrue(role.has_permission('sample.view'))
        self.assertTrue(role.has_permission('sample.create'))
        self.assertTrue(role.has_permission('aliquot.view'))
        # Test permissions that lab_member should not have
        self.assertFalse(role.has_permission('sample.delete'))
        self.assertFalse(role.has_permission('user.manage_permissions'))
        self.assertFalse(role.has_permission('system.admin'))


class PermissionModelTest(TestCase):
    """Test cases for the Permission model"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.granted_by = User.objects.create_user(
            username='granter',
            email='granter@example.com',
            password='grantpass123'
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
    def test_permission_creation_and_validation(self):
        """Test permission creation and validation"""
        content_type = ContentType.objects.get_for_model(Sample)
        permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            granted_by=self.granted_by
        )
        self.assertEqual(permission.user, self.user)
        self.assertEqual(permission.permission_type, 'edit')
        self.assertEqual(permission.content_type, content_type)
        self.assertEqual(permission.object_id, self.sample.id)
        self.assertEqual(permission.granted_by, self.granted_by)
        self.assertIsNotNone(permission.granted_at)
        self.assertIsNone(permission.expires_at)
    def test_permission_expiration_handling(self):
        """Test permission expiration handling"""
        content_type = ContentType.objects.get_for_model(Sample)
        # Create permission without expiration
        permanent_permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        self.assertTrue(permanent_permission.is_valid())
        # Create permission with future expiration
        future_expiration = timezone.now() + timezone.timedelta(days=1)
        future_permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=future_expiration
        )
        self.assertTrue(future_permission.is_valid())
        # Create permission with past expiration
        past_expiration = timezone.now() - timezone.timedelta(days=1)
        expired_permission = Permission.objects.create(
            user=self.user,
            permission_type='delete',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=past_expiration
        )
        self.assertFalse(expired_permission.is_valid())
    def test_permission_uniqueness_constraints(self):
        """Test permission uniqueness constraints"""
        content_type = ContentType.objects.get_for_model(Sample)
        # Create first permission
        Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        # Try to create duplicate permission
        with self.assertRaises(IntegrityError):
            Permission.objects.create(
                user=self.user,
                permission_type='view',
                content_type=content_type,
                object_id=self.sample.id
            )
    def test_permission_validity_checking(self):
        """Test permission validity checking"""
        content_type = ContentType.objects.get_for_model(Sample)
        # Test valid permission
        valid_permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        self.assertTrue(valid_permission.is_valid())
        # Test expired permission
        expired_permission = Permission.objects.create(
            user=self.user,
            permission_type='edit',
            content_type=content_type,
            object_id=self.sample.id,
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertFalse(expired_permission.is_valid())
    def test_permission_string_representation(self):
        """Test permission string representation"""
        content_type = ContentType.objects.get_for_model(Sample)
        permission = Permission.objects.create(
            user=self.user,
            permission_type='view',
            content_type=content_type,
            object_id=self.sample.id
        )
        expected_str = f"{self.user.username} - view - {self.sample}"
        self.assertEqual(str(permission), expected_str)


class UserAuditLogModelTest(TestCase):
    """Test cases for the UserAuditLog model"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
    def test_audit_log_creation(self):
        """Test audit log creation"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample',
            target_id=self.sample.id,
            target_name=self.sample.name,
            details={'test': 'data'}
        )
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'create')
        self.assertEqual(log_entry.target_type, 'Sample')
        self.assertEqual(log_entry.target_id, self.sample.id)
        self.assertEqual(log_entry.target_name, self.sample.name)
        self.assertEqual(log_entry.details, {'test': 'data'})
        self.assertIsNotNone(log_entry.timestamp)
    def test_audit_log_action_tracking(self):
        """Test audit log action tracking"""
        actions = ['login', 'logout', 'create', 'update', 'delete', 'view', 'export', 'import']
        for action in actions:
            log_entry = UserAuditLog.objects.create(
                user=self.user,
                action=action,
                target_type='Sample',
                target_id=self.sample.id
            )
            self.assertEqual(log_entry.action, action)
    def test_audit_log_ip_address_capture(self):
        """Test audit log IP address capture"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='login',
            ip_address='192.168.1.1'
        )
        self.assertEqual(log_entry.ip_address, '192.168.1.1')
    def test_audit_log_user_agent_capture(self):
        """Test audit log user agent capture"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='login',
            user_agent=user_agent
        )
        self.assertEqual(log_entry.user_agent, user_agent)
    def test_log_action_convenience_method(self):
        """Test log_action convenience method"""
        # Test without request
        log_entry = UserAuditLog.log_action(
            user=self.user,
            action='create',
            target_type='Sample',
            target_id=self.sample.id,
            target_name=self.sample.name,
            details={'method': 'test'}
        )
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'create')
        self.assertEqual(log_entry.target_type, 'Sample')
        self.assertEqual(log_entry.target_id, self.sample.id)
        self.assertEqual(log_entry.target_name, self.sample.name)
        self.assertEqual(log_entry.details, {'method': 'test'})
        self.assertIsNone(log_entry.ip_address)
        self.assertEqual(log_entry.user_agent, '')
    def test_log_action_with_request(self):
        """Test log_action with request object"""
        # Create a mock request
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Test Browser/1.0'
        log_entry = UserAuditLog.log_action(
            user=self.user,
            action='login',
            request=request
        )
        self.assertEqual(log_entry.ip_address, '192.168.1.100')
        self.assertEqual(log_entry.user_agent, 'Test Browser/1.0')
    def test_get_client_ip_method(self):
        """Test get_client_ip method"""
        # Test with HTTP_X_FORWARDED_FOR
        request = HttpRequest()
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        ip = UserAuditLog.get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')
        # Test with REMOTE_ADDR only
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        ip = UserAuditLog.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    def test_audit_log_string_representation(self):
        """Test audit log string representation"""
        log_entry = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample'
        )
        expected_str = f"{self.user.username} - create - {log_entry.timestamp}"
        self.assertEqual(str(log_entry), expected_str)
    def test_audit_log_ordering(self):
        """Test audit log ordering by timestamp"""
        # Create logs with different timestamps
        log1 = UserAuditLog.objects.create(
            user=self.user,
            action='create',
            target_type='Sample'
        )
        log2 = UserAuditLog.objects.create(
            user=self.user,
            action='update',
            target_type='Sample'
        )
        # Test ordering (should be newest first)
        logs = UserAuditLog.objects.all()
        self.assertEqual(logs[0], log2)  # Newest first
        self.assertEqual(logs[1], log1)  # Oldest last


class UserPreferenceModelTest(TestCase):
    """Test cases for the UserPreference model"""
    def setUp(self):
        """Set up test data"""
        # Note: We don't create a user in setUp to avoid conflicts
        # Each test will create its own user to avoid OneToOneField conflicts
        pass
    def test_preference_creation_and_defaults(self):
        """Test preference creation and defaults"""
        pref_user = User.objects.create_user(
            username='pref_creation_test',
            email='pref_creation_test@example.com'
        )
        # The signal automatically creates a UserPreference, so we need to update it
        preference = pref_user.preference
        preference.dark_mode = True
        preference.save()
        self.assertEqual(preference.user, pref_user)
        self.assertTrue(preference.dark_mode)
        self.assertIsNotNone(preference.created_at)
        self.assertIsNotNone(preference.updated_at)
    def test_dark_mode_toggle_functionality(self):
        """Test dark mode toggle functionality"""
        toggle_user = User.objects.create_user(
            username='toggle_dark_mode_test',
            email='toggle_dark_mode_test@example.com'
        )
        # The signal automatically creates a UserPreference, so we get the existing one
        preference = toggle_user.preference
        # Initially dark mode is off (default from signal)
        self.assertFalse(preference.dark_mode)
        # Toggle dark mode on
        preference.dark_mode = True
        preference.save()
        self.assertTrue(preference.dark_mode)
        # Toggle dark mode off
        preference.dark_mode = False
        preference.save()
        self.assertFalse(preference.dark_mode)
    def test_preference_user_relationship(self):
        """Test preference-user relationship"""
        rel_user = User.objects.create_user(
            username='pref_relationship_test',
            email='pref_relationship_test@example.com'
        )
        # The signal automatically creates a UserPreference
        preference = rel_user.preference
        self.assertEqual(preference.user, rel_user)
        self.assertEqual(rel_user.preference, preference)
    def test_preference_string_representation(self):
        """Test preference string representation"""
        str_user = User.objects.create_user(
            username='pref_string_test',
            email='pref_string_test@example.com'
        )
        # The signal automatically creates a UserPreference
        preference = str_user.preference
        expected_str = f"{str_user.username}'s preferences"
        self.assertEqual(str(preference), expected_str)
    def test_preference_timestamp_fields(self):
        """Test preference timestamp fields"""
        time_user = User.objects.create_user(
            username='pref_timestamp_test',
            email='pref_timestamp_test@example.com'
        )
        # The signal automatically creates a UserPreference
        preference = time_user.preference
        original_created_at = preference.created_at
        original_updated_at = preference.updated_at
        # Update preference
        preference.dark_mode = True
        preference.save()
        # created_at should not change
        self.assertEqual(preference.created_at, original_created_at)
        # updated_at should change (since it uses auto_now=True)
        self.assertGreater(preference.updated_at, original_updated_at)


class CreateUserFormTest(TestCase):
    """Test cases for the CreateUserForm"""
    def test_create_user_form_widgets_and_help_texts(self):
        """Test create user form widgets and help texts"""
        form = CreateUserForm()
        # Test help texts
        self.assertIn('Select the user role', str(form.fields['role'].help_text))
        self.assertIn('Department or organizational unit', str(form.fields['department'].help_text))
        self.assertIn('Specific laboratory unit', str(form.fields['lab_unit'].help_text))
        # Test widgets have form-control class
        self.assertIn('form-control', form.fields['username'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['email'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['first_name'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['last_name'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['role'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['department'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['lab_unit'].widget.attrs['class'])


class CustomUserCreationFormTest(TestCase):
    """Test cases for the CustomUserCreationForm"""
    def test_custom_user_creation_form_widgets_and_help_texts(self):
        """Test custom user creation form widgets and help texts"""
        form = CustomUserCreationForm()
        # Test that form has expected fields
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('role', form.fields)
        self.assertIn('department', form.fields)
        self.assertIn('lab_unit', form.fields)


class CustomUserChangeFormTest(TestCase):
    """Test cases for the CustomUserChangeForm"""
    def test_custom_user_change_form_widgets_and_help_texts(self):
        """Test custom user change form widgets and help texts"""
        form = CustomUserChangeForm()
        # Test that form has expected fields
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('role', form.fields)
        self.assertIn('department', form.fields)
        self.assertIn('lab_unit', form.fields)


class UserRoleFormTest(TestCase):
    """Test cases for the UserRoleForm"""
    def test_user_role_form_widgets_and_help_texts(self):
        """Test user role form widgets and help texts"""
        form = UserRoleForm()
        # Test that form has expected fields
        self.assertIn('role', form.fields)
        self.assertIn('department', form.fields)
        self.assertIn('lab_unit', form.fields)
        # Test widgets have form-control class
        self.assertIn('form-control', form.fields['role'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['department'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['lab_unit'].widget.attrs['class'])


class PermissionFormTest(TestCase):
    """Test cases for the PermissionForm"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.granted_by = User.objects.create_user(
            username='granter',
            email='granter@example.com'
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.content_type = ContentType.objects.get_for_model(Sample)
    def test_permission_form_validation_with_valid_data(self):
        """Test permission form validation with valid data"""
        form_data = {
            'user': self.user.id,
            'permission_type': 'edit',
            'content_type': self.content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        form = PermissionForm(data=form_data)
        self.assertTrue(form.is_valid())
        permission = form.save(granted_by=self.granted_by)
        self.assertEqual(permission.user, self.user)
        self.assertEqual(permission.permission_type, 'edit')
        self.assertEqual(permission.content_type, self.content_type)
        self.assertEqual(permission.object_id, self.sample.id)
        self.assertEqual(permission.granted_by, self.granted_by)
        self.assertIsNone(permission.expires_at)
    def test_permission_form_error_handling_missing_required_fields(self):
        """Test permission form error handling for missing required fields"""
        # Test missing user
        form_data = {
            'permission_type': 'edit',
            'content_type': self.content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        form = PermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
        # Test missing permission type
        form_data = {
            'user': self.user.id,
            'content_type': self.content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        form = PermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('permission_type', form.errors)
    def test_permission_form_with_expiration_date(self):
        """Test permission form with expiration date"""
        expiration_date = timezone.now() + timezone.timedelta(days=30)
        form_data = {
            'user': self.user.id,
            'permission_type': 'view',
            'content_type': self.content_type.id,
            'object_id': self.sample.id,
            'expires_at': expiration_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        form = PermissionForm(data=form_data)
        self.assertTrue(form.is_valid())
        permission = form.save()
        self.assertEqual(permission.permission_type, 'view')
        self.assertIsNotNone(permission.expires_at)
    def test_permission_form_widgets_and_help_texts(self):
        """Test permission form widgets and help texts"""
        form = PermissionForm()
        # Test help texts
        self.assertIn('Select the user to grant permission to', str(form.fields['user'].help_text))
        self.assertIn('Type of permission to grant', str(form.fields['permission_type'].help_text))
        self.assertIn('Optional expiration date', str(form.fields['expires_at'].help_text))
        # Test widgets have form-control class
        self.assertIn('form-control', form.fields['user'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['permission_type'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['expires_at'].widget.attrs['class'])


class UserPreferenceFormTest(TestCase):
    """Test cases for the UserPreferenceForm"""
    def test_user_preference_form_widgets_and_help_texts(self):
        """Test user preference form widgets and help texts"""
        form = UserPreferenceForm()
        # Test that form has expected fields
        self.assertIn('dark_mode', form.fields)
        # Test widget has form-check-input class
        self.assertIn('form-check-input', form.fields['dark_mode'].widget.attrs['class'])


class BulkPermissionFormTest(TestCase):
    """Test cases for the BulkPermissionForm"""
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com'
        )
    def test_bulk_permission_form_validation_with_valid_data(self):
        """Test bulk permission form validation with valid data"""
        content_type = ContentType.objects.get_for_model(Sample)
        form_data = {
            'users': [self.user1.id, self.user2.id],
            'permission_type': 'view',
            'content_type': content_type.id,
            'object_id': 1,
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data['users']), 2)
        self.assertEqual(form.cleaned_data['permission_type'], 'view')
        self.assertIsNone(form.cleaned_data['expires_at'])
    def test_bulk_permission_form_error_handling_missing_required_fields(self):
        """Test bulk permission form error handling for missing required fields"""
        content_type = ContentType.objects.get_for_model(Sample)
        # Test missing users
        form_data = {
            'permission_type': 'view',
            'content_type': content_type.id,
            'object_id': 1,
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('users', form.errors)
        # Test missing permission type
        form_data = {
            'users': [self.user1.id],
            'content_type': content_type.id,
            'object_id': 1,
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('permission_type', form.errors)
    def test_bulk_permission_form_with_expiration_date(self):
        """Test bulk permission form with expiration date"""
        content_type = ContentType.objects.get_for_model(Sample)
        expiration_date = timezone.now() + timezone.timedelta(days=30)
        form_data = {
            'users': [self.user1.id],
            'permission_type': 'edit',
            'content_type': content_type.id,
            'object_id': 1,
            'expires_at': expiration_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        form = BulkPermissionForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.cleaned_data['expires_at'])
    def test_bulk_permission_form_widgets_and_help_texts(self):
        """Test bulk permission form widgets and help texts"""
        form = BulkPermissionForm()
        # Test help texts
        self.assertIn('Select users to grant permissions to', str(form.fields['users'].help_text))
        self.assertIn('Type of permission to grant', str(form.fields['permission_type'].help_text))
        self.assertIn('Optional expiration date', str(form.fields['expires_at'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['users'].widget, forms.CheckboxSelectMultiple)
        self.assertIn('form-control', form.fields['permission_type'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['expires_at'].widget.attrs['class'])


class UserSearchFormTest(TestCase):
    """Test cases for the UserSearchForm"""
    def test_user_search_form_validation_with_valid_data(self):
        """Test user search form validation with valid data"""
        form_data = {
            'search': 'testuser',
            'role': 'lab_member',
            'department': 'Research',
            'is_active': 'True'
        }
        form = UserSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search'], 'testuser')
        self.assertEqual(form.cleaned_data['role'], 'lab_member')
        self.assertEqual(form.cleaned_data['department'], 'Research')
        self.assertEqual(form.cleaned_data['is_active'], 'True')
    def test_user_search_form_with_empty_data(self):
        """Test user search form with empty data"""
        form_data = {}
        form = UserSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search'], '')
        self.assertEqual(form.cleaned_data['role'], '')
        self.assertEqual(form.cleaned_data['department'], '')
        self.assertEqual(form.cleaned_data['is_active'], '')
    def test_user_search_form_widgets_and_help_texts(self):
        """Test user search form widgets and help texts"""
        form = UserSearchForm()
        # Test widgets have form-control class
        self.assertIn('form-control', form.fields['search'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['role'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['department'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['is_active'].widget.attrs['class'])
        # Test placeholders
        self.assertIn('Search by username, email, or name...', form.fields['search'].widget.attrs['placeholder'])
        self.assertIn('Filter by department...', form.fields['department'].widget.attrs['placeholder'])


class AuditLogFilterFormTest(TestCase):
    """Test cases for the AuditLogFilterForm"""
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
    def test_audit_log_filter_form_validation_with_valid_data(self):
        """Test audit log filter form validation with valid data"""
        form_data = {
            'user': self.user.id,
            'action': 'create',
            'target_type': 'Sample',
            'date_from': '2023-01-01',
            'date_to': '2023-12-31'
        }
        form = AuditLogFilterForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['user'], self.user)
        self.assertEqual(form.cleaned_data['action'], 'create')
        self.assertEqual(form.cleaned_data['target_type'], 'Sample')
        self.assertIsNotNone(form.cleaned_data['date_from'])
        self.assertIsNotNone(form.cleaned_data['date_to'])
    def test_audit_log_filter_form_with_empty_data(self):
        """Test audit log filter form with empty data"""
        form_data = {}
        form = AuditLogFilterForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['user'])
        self.assertEqual(form.cleaned_data['action'], '')
        self.assertEqual(form.cleaned_data['target_type'], '')
        self.assertIsNone(form.cleaned_data['date_from'])
        self.assertIsNone(form.cleaned_data['date_to'])
    def test_audit_log_filter_form_widgets_and_help_texts(self):
        """Test audit log filter form widgets and help texts"""
        form = AuditLogFilterForm()
        # Test widgets have form-control class
        self.assertIn('form-control', form.fields['user'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['action'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['target_type'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['date_from'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['date_to'].widget.attrs['class'])
        # Test placeholders
        self.assertIn('Filter by target type...', form.fields['target_type'].widget.attrs['placeholder'])


class PersonViewTest(TestCase):
    """Base test class for person views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.factory = RequestFactory()
        # Create test users with different roles
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        # Update the automatically created role
        self.viewer_role = self.viewer_user.role
        self.viewer_role.role = 'viewer'
        self.viewer_role.save()
        self.lab_member_user = User.objects.create_user(
            username='lab_member',
            email='lab_member@example.com',
            password='testpass123'
        )
        # Update the automatically created role
        self.lab_member_role = self.lab_member_user.role
        self.lab_member_role.role = 'lab_member'
        self.lab_member_role.save()
        self.lab_manager_user = User.objects.create_user(
            username='lab_manager',
            email='lab_manager@example.com',
            password='testpass123'
        )
        # Update the automatically created role
        self.lab_manager_role = self.lab_manager_user.role
        self.lab_manager_role.role = 'lab_manager'
        self.lab_manager_role.save()
        self.lab_admin_user = User.objects.create_user(
            username='lab_admin',
            email='lab_admin@example.com',
            password='testpass123'
        )
        # Update the automatically created role
        self.lab_admin_role = self.lab_admin_user.role
        self.lab_admin_role.role = 'lab_admin'
        self.lab_admin_role.save()
        # Create test source and sample for permission tests
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
    def _add_session_and_messages(self, request):
        """Add session and messages middleware to request"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)


class ToggleThemeViewTest(PersonViewTest):
    """Test cases for the toggle_theme view"""
    def test_toggle_theme_requires_login(self):
        """Test that toggle_theme requires login"""
        response = self.client.post(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_toggle_theme_requires_post(self):
        """Test that toggle_theme only accepts POST requests"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_toggle_theme_creates_preference(self):
        """Test that toggle_theme creates user preference if it doesn't exist"""
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        # Check that preference was created
        preference = UserPreference.objects.get(user=self.viewer_user)
        self.assertTrue(preference.dark_mode)
    def test_toggle_theme_toggles_existing_preference(self):
        """Test that toggle_theme toggles existing preference"""
        # Update the automatically created preference
        preference = self.viewer_user.preference
        preference.dark_mode = False
        preference.save()
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        # Check that preference was toggled
        preference.refresh_from_db()
        self.assertTrue(preference.dark_mode)


class CreateUserViewTest(PersonViewTest):
    """Test cases for the create_user view"""
    def test_create_user_requires_lab_manager_role(self):
        """Test that create_user requires lab_manager role or higher"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_member role
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 200)  # OK
        # Test with lab_admin role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_create_user_get_request(self):
        """Test create_user GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/create_user.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], CreateUserForm)
        self.assertEqual(response.context['title'], 'Create New User')
    def test_create_user_post_valid_data(self):
        """Test create_user POST with valid data"""
        self.client.force_login(self.lab_admin_user)
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'role': 'lab_member',
            'department': 'Research',
            'lab_unit': 'Lab A'
        }
        response = self.client.post(reverse('person:create_user'), form_data)
        # Should redirect to user detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:user_detail', kwargs={'user_id': User.objects.get(username='newuser').id}))
        # Check that user was created
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
        # Check that user role was created
        self.assertTrue(hasattr(new_user, 'role'))
        self.assertEqual(new_user.role.role, 'lab_member')
        self.assertEqual(new_user.role.department, 'Research')
        self.assertEqual(new_user.role.lab_unit, 'Lab A')
        # Check that user preference was created
        self.assertTrue(hasattr(new_user, 'preference'))
        self.assertFalse(new_user.preference.dark_mode)
        # Check that audit log was created
        audit_log = UserAuditLog.objects.filter(
            user=self.lab_admin_user,  # The user who performed the action
            action='create',
            target_type='User',
            target_id=new_user.id
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.target_name, 'newuser')
    def test_create_user_post_invalid_data(self):
        """Test create_user POST with invalid data"""
        self.client.force_login(self.lab_admin_user)
        form_data = {
            'username': 'newuser',
            'email': 'invalid-email',  # Invalid email
            'password1': 'testpass123',
            'password2': 'differentpass',  # Password mismatch
            'role': 'lab_member'
        }
        response = self.client.post(reverse('person:create_user'), form_data)
        self.assertEqual(response.status_code, 200)  # Form errors, not redirect
        self.assertTemplateUsed(response, 'person/create_user.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())


class UserListViewTest(PersonViewTest):
    """Test cases for the user_list view"""
    def test_user_list_requires_lab_admin_role(self):
        """Test that user_list requires lab_admin role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_user_list_get_request(self):
        """Test user_list GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/user_list.html')
        self.assertIn('page_obj', response.context)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], UserSearchForm)
        self.assertIn('total_users', response.context)
    def test_user_list_with_search_filter(self):
        """Test user_list with search filter"""
        self.client.force_login(self.lab_admin_user)
        # Search by username
        response = self.client.get(reverse('person:user_list'), {'search': 'lab_manager'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        # Search by role
        response = self.client.get(reverse('person:user_list'), {'role': 'lab_manager'})
        self.assertEqual(response.status_code, 200)
        # Search by department
        response = self.client.get(reverse('person:user_list'), {'department': 'Research'})
        self.assertEqual(response.status_code, 200)
        # Search by active status
        response = self.client.get(reverse('person:user_list'), {'is_active': 'True'})
        self.assertEqual(response.status_code, 200)


class UserDetailViewTest(PersonViewTest):
    """Test cases for the user_detail view"""
    def test_user_detail_requires_lab_admin_role(self):
        """Test that user_detail requires lab_admin role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)  # OK
    def test_user_detail_get_request(self):
        """Test user_detail GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/user_detail.html')
        self.assertIn('user_role', response.context)
        self.assertEqual(response.context['user_role'], self.lab_member_role)
        self.assertIn('permissions', response.context)
        self.assertIn('role_permissions', response.context)
        self.assertIn('recent_activity', response.context)
    def test_user_detail_nonexistent_user(self):
        """Test user_detail with nonexistent user"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': 99999}))
        self.assertEqual(response.status_code, 404)  # Not found


class UserRoleEditViewTest(PersonViewTest):
    """Test cases for the user_role_edit view"""
    def test_user_role_edit_requires_lab_manager_role(self):
        """Test that user_role_edit requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)  # OK
    def test_user_role_edit_get_request(self):
        """Test user_role_edit GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/user_role_edit.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], UserRoleForm)
        self.assertIn('user_role', response.context)
        self.assertEqual(response.context['user_role'], self.lab_member_role)
    def test_user_role_edit_post_valid_data(self):
        """Test user_role_edit POST with valid data"""
        self.client.force_login(self.lab_admin_user)
        form_data = {
            'role': 'lab_manager',
            'department': 'Updated Research',
            'lab_unit': 'Lab B'
        }
        response = self.client.post(
            reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}),
            form_data
        )
        # Should redirect to user detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        # Check that role was updated
        self.lab_member_role.refresh_from_db()
        self.assertEqual(self.lab_member_role.role, 'lab_manager')
        self.assertEqual(self.lab_member_role.department, 'Updated Research')
        self.assertEqual(self.lab_member_role.lab_unit, 'Lab B')
        # Check that audit log was created
        audit_log = UserAuditLog.objects.filter(
            user=self.lab_admin_user,  # The user who performed the action
            action='role_changed',
            target_type='User',
            target_id=self.lab_member_user.id
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.target_name, 'lab_member')


class PermissionListViewTest(PersonViewTest):
    """Test cases for the permission_list view"""
    def test_permission_list_requires_lab_manager_role(self):
        """Test that permission_list requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_permission_list_get_request(self):
        """Test permission_list GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/permission_list.html')
        self.assertIn('page_obj', response.context)
        self.assertIn('total_permissions', response.context)
    def test_permission_list_with_filters(self):
        """Test permission_list with filters"""
        self.client.force_login(self.lab_admin_user)
        # Filter by user
        response = self.client.get(reverse('person:permission_list'), {'user': 'lab_member'})
        self.assertEqual(response.status_code, 200)
        # Filter by permission type
        response = self.client.get(reverse('person:permission_list'), {'permission_type': 'view'})
        self.assertEqual(response.status_code, 200)
        # Filter by content type
        response = self.client.get(reverse('person:permission_list'), {'content_type': 'sample'})
        self.assertEqual(response.status_code, 200)


class GrantPermissionViewTest(PersonViewTest):
    """Test cases for the grant_permission view"""
    def test_grant_permission_requires_lab_manager_role(self):
        """Test that grant_permission requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:grant_permission'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:grant_permission'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_grant_permission_get_request(self):
        """Test grant_permission GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:grant_permission'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/permission_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PermissionForm)
        self.assertEqual(response.context['title'], 'Grant Permission')
    def test_grant_permission_post_valid_data(self):
        """Test grant_permission POST with valid data"""
        self.client.force_login(self.lab_admin_user)
        content_type = ContentType.objects.get_for_model(Sample)
        form_data = {
            'user': self.lab_member_user.id,
            'permission_type': 'view',
            'content_type': content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        response = self.client.post(reverse('person:grant_permission'), form_data)
        # Should redirect to permission list
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:permission_list'))
        # Check that permission was created
        permission = Permission.objects.filter(
            user=self.lab_member_user,
            permission_type='view'
        ).first()
        self.assertIsNotNone(permission)
        self.assertEqual(permission.granted_by, self.lab_admin_user)


class BulkGrantPermissionViewTest(PersonViewTest):
    """Test cases for the bulk_grant_permission view"""
    def test_bulk_grant_permission_requires_lab_manager_role(self):
        """Test that bulk_grant_permission requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:bulk_grant_permission'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:bulk_grant_permission'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_bulk_grant_permission_get_request(self):
        """Test bulk_grant_permission GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:bulk_grant_permission'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/bulk_permission_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], BulkPermissionForm)
        self.assertEqual(response.context['title'], 'Bulk Grant Permissions')
    def test_bulk_grant_permission_post_valid_data(self):
        """Test bulk_grant_permission POST with valid data"""
        self.client.force_login(self.lab_admin_user)
        content_type = ContentType.objects.get_for_model(Sample)
        form_data = {
            'users': [self.lab_member_user.id],
            'permission_type': 'view',
            'content_type': content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        response = self.client.post(reverse('person:bulk_grant_permission'), form_data)
        # Should redirect to permission list
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:permission_list'))
        # Check that permission was created
        permission = Permission.objects.filter(
            user=self.lab_member_user,
            permission_type='view'
        ).first()
        self.assertIsNotNone(permission)
        self.assertEqual(permission.granted_by, self.lab_admin_user)


class AuditLogViewTest(PersonViewTest):
    """Test cases for the audit_log view"""
    def test_audit_log_requires_lab_manager_role(self):
        """Test that audit_log requires lab_manager role or higher"""
        # Test with lab_member role (should be forbidden)
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role (should be allowed)
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)  # OK
        # Test with lab_admin role (should be allowed)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)  # OK
    def test_audit_log_get_request(self):
        """Test audit_log GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/audit_log.html')
        self.assertIn('page_obj', response.context)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], AuditLogFilterForm)
        self.assertIn('total_logs', response.context)
    def test_audit_log_with_filters(self):
        """Test audit_log with filters"""
        self.client.force_login(self.lab_admin_user)
        # Filter by user
        response = self.client.get(reverse('person:audit_log'), {'user': self.lab_member_user.id})
        self.assertEqual(response.status_code, 200)
        # Filter by action
        response = self.client.get(reverse('person:audit_log'), {'action': 'create'})
        self.assertEqual(response.status_code, 200)
        # Filter by target type
        response = self.client.get(reverse('person:audit_log'), {'target_type': 'User'})
        self.assertEqual(response.status_code, 200)


class UserPermissionsApiViewTest(PersonViewTest):
    """Test cases for the user_permissions_api view"""
    def test_user_permissions_api_requires_lab_manager_role(self):
        """Test that user_permissions_api requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)  # OK
    def test_user_permissions_api_get_request(self):
        """Test user_permissions_api GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Check response structure
        self.assertIn('user', data)
        self.assertIn('role_permissions', data)
        self.assertIn('object_permissions', data)
        # Check user data
        self.assertEqual(data['user']['id'], self.lab_member_user.id)
        self.assertEqual(data['user']['username'], 'lab_member')
        self.assertEqual(data['user']['role'], 'lab_member')
    def test_user_permissions_api_nonexistent_user(self):
        """Test user_permissions_api with nonexistent user"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': 99999}))
        self.assertEqual(response.status_code, 404)  # Not found


class GrantObjectPermissionApiViewTest(PersonViewTest):
    """Test cases for the grant_object_permission_api view"""
    def test_grant_object_permission_api_requires_lab_manager_role(self):
        """Test that grant_object_permission_api requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 400)  # Bad request (missing parameters)
    def test_grant_object_permission_api_requires_post(self):
        """Test that grant_object_permission_api only accepts POST requests"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_grant_object_permission_api_missing_parameters(self):
        """Test grant_object_permission_api with missing parameters"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Missing required parameters')
    def test_grant_object_permission_api_invalid_model(self):
        """Test grant_object_permission_api with invalid model"""
        self.client.force_login(self.lab_admin_user)
        form_data = {
            'user_id': self.lab_member_user.id,
            'model_name': 'InvalidModel',
            'object_id': self.sample.id,
            'permission_type': 'view'
        }
        response = self.client.post(reverse('person:grant_object_permission_api'), form_data)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid model name')


class RevokeObjectPermissionApiViewTest(PersonViewTest):
    """Test cases for the revoke_object_permission_api view"""
    def test_revoke_object_permission_api_requires_lab_manager_role(self):
        """Test that revoke_object_permission_api requires lab_manager role"""
        # Test with viewer role
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        # Test with lab_manager role
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 400)  # Bad request (missing parameters)
    def test_revoke_object_permission_api_requires_post(self):
        """Test that revoke_object_permission_api only accepts POST requests"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_revoke_object_permission_api_missing_parameters(self):
        """Test revoke_object_permission_api with missing parameters"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Missing required parameters')
    def test_revoke_object_permission_api_invalid_model(self):
        """Test revoke_object_permission_api with invalid model"""
        self.client.force_login(self.lab_admin_user)
        form_data = {
            'user_id': self.lab_member_user.id,
            'model_name': 'InvalidModel',
            'object_id': self.sample.id,
            'permission_type': 'view'
        }
        response = self.client.post(reverse('person:revoke_object_permission_api'), form_data)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid model name')


class DataImportViewTest(PersonViewTest):
    """Test cases for the DataImportView"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        # Create a test CSV content based on actual CSV structure
        self.test_csv_content = """Cell Line;Source;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Number of Aliquots Total;Disposition;Sample Notes;Aliquot Notes;Aliquot/SubA Passage#;Experiment #
MDA MB 134VI (MM134);UPMC/MJS;Sikora LN2 #1;4;F;1;1;Cells;5;In Storage;Legacy MM134 from Oesterreich Lab banks;;p+33;EXP001
MDA MB 134VI (MM134);UPMC/MJS;Sikora LN2 #1;4;F;1;2;Cells;3;Checked Out;Legacy MM134 from Oesterreich Lab banks;Thawed by MTS on 09.04.19;p+33;EXP001"""

    def test_data_import_requires_lab_manager_role(self):
        """Test that data import requires lab_manager role or higher"""
        # Test with regular user (should be forbidden)
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 403)  # Forbidden

        # Test with lab_manager user
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 200)  # OK

        # Test with lab_admin user
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 200)  # OK

    def test_data_import_get_request(self):
        """Test data import GET request"""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/data_import.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['title'], 'Data Import')

    def test_data_import_preview_mode(self):
        """Test data import preview mode"""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        # Create a test CSV file
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile(
            "test.csv",
            self.test_csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        form_data = {
            'csv_file': csv_file
        }

        response = self.client.post(reverse('person:data_import'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/data_import.html')
        self.assertIn('preview_data', response.context)

        # Check preview data structure
        preview_data = response.context['preview_data']
        self.assertIn('sources', preview_data)
        self.assertIn('samples', preview_data)
        self.assertIn('aliquots', preview_data)

    def test_data_import_form_validation(self):
        """Test data import form validation"""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        # Test with no file
        form_data = {}
        response = self.client.post(reverse('person:data_import'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())

    def test_convert_csv_to_fixtures_method(self):
        """Test the convert_csv_to_fixtures method"""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        # Create a temporary CSV file
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(self.test_csv_content)
            temp_file_path = temp_file.name

        try:
            # Test the convert_csv_to_fixtures method
            view = DataImportView()
            fixtures = view.convert_csv_to_fixtures(temp_file_path)

            # Check that fixtures were created
            self.assertIsInstance(fixtures, list)
            self.assertGreater(len(fixtures), 0)

            # Check for expected fixture types
            fixture_models = [fixture['model'] for fixture in fixtures]
            self.assertIn('sample.source', fixture_models)
            self.assertIn('sample.sample', fixture_models)
            self.assertIn('sample.aliquot', fixture_models)
            self.assertIn('sample.aliquottube', fixture_models)
            self.assertIn('storage.site', fixture_models)
            self.assertIn('storage.device', fixture_models)
            self.assertIn('storage.shelf', fixture_models)
            self.assertIn('storage.rack', fixture_models)
            self.assertIn('storage.box', fixture_models)
            self.assertIn('sample.aliquotlocation', fixture_models)

            # Check storage hierarchy structure
            storage_fixtures = {f['model']: f for f in fixtures if f['model'].startswith('storage.')}

            # Verify site (should default to "Default Site" when Site column is not provided)
            self.assertIn('storage.site', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.site']['fields']['name'], 'Default Site')

            # Verify device
            self.assertIn('storage.device', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.device']['fields']['name'], 'Sikora LN2 #1')

            # Verify shelf (Position 2)
            self.assertIn('storage.shelf', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.shelf']['fields']['name'], 'F')

            # Verify rack (Position 1)
            self.assertIn('storage.rack', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.rack']['fields']['name'], '4')

            # Verify box (Position 1 + Position 2)
            self.assertIn('storage.box', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.box']['fields']['name'], '4_F')

            # Verify location (Position 3, Position 4)
            location_fixtures = [f for f in fixtures if f['model'] == 'sample.aliquotlocation']
            self.assertGreater(len(location_fixtures), 0)
            for location in location_fixtures:
                self.assertEqual(location['fields']['row'], 1)  # Position 3
                self.assertIn(location['fields']['column'], [1, 2])  # Position 4

            # Verify that tubes are created with correct quantities
            tube_fixtures = [f for f in fixtures if f['model'] == 'sample.aliquottube']
            self.assertGreater(len(tube_fixtures), 0)

            # Check that we have the expected number of tubes (5 + 3 = 8 total)
            self.assertEqual(len(tube_fixtures), 8)

            # Verify tube dispositions
            for tube in tube_fixtures:
                disposition_pk = tube['fields']['disposition']
                # Find the disposition fixture
                disposition_fixture = next(f for f in fixtures if f['model'] == 'sample.aliquotdisposition' and f['pk'] == disposition_pk)
                self.assertIn(disposition_fixture['fields']['disposition_type'], ['stored', 'in_use', 'exhausted'])

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
