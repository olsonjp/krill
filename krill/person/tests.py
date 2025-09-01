from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django import forms

from .models import UserRole, Permission, UserAuditLog, UserPreference
from .forms import (
    CreateUserForm, CustomUserCreationForm, CustomUserChangeForm,
    UserRoleForm, PermissionForm, UserPreferenceForm, BulkPermissionForm,
    UserSearchForm, AuditLogFilterForm
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
            'expires_at': ''
        }
        form = PermissionForm(
            data=form_data,
            content_type=self.content_type,
            object_id=self.sample.id
        )
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
            'expires_at': ''
        }
        form = PermissionForm(
            data=form_data,
            content_type=self.content_type,
            object_id=self.sample.id
        )
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
        
        # Test missing permission type
        form_data = {
            'user': self.user.id,
            'expires_at': ''
        }
        form = PermissionForm(
            data=form_data,
            content_type=self.content_type,
            object_id=self.sample.id
        )
        self.assertFalse(form.is_valid())
        self.assertIn('permission_type', form.errors)
    
    def test_permission_form_with_expiration_date(self):
        """Test permission form with expiration date"""
        expiration_date = timezone.now() + timezone.timedelta(days=30)
        form_data = {
            'user': self.user.id,
            'permission_type': 'view',
            'expires_at': expiration_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        form = PermissionForm(
            data=form_data,
            content_type=self.content_type,
            object_id=self.sample.id
        )
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
        form_data = {
            'users': [self.user1.id, self.user2.id],
            'permission_type': 'view',
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        self.assertEqual(len(form.cleaned_data['users']), 2)
        self.assertEqual(form.cleaned_data['permission_type'], 'view')
        self.assertIsNone(form.cleaned_data['expires_at'])
    
    def test_bulk_permission_form_error_handling_missing_required_fields(self):
        """Test bulk permission form error handling for missing required fields"""
        # Test missing users
        form_data = {
            'permission_type': 'view',
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('users', form.errors)
        
        # Test missing permission type
        form_data = {
            'users': [self.user1.id],
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('permission_type', form.errors)
    
    def test_bulk_permission_form_with_expiration_date(self):
        """Test bulk permission form with expiration date"""
        expiration_date = timezone.now() + timezone.timedelta(days=30)
        form_data = {
            'users': [self.user1.id],
            'permission_type': 'edit',
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
