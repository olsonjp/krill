from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django import forms

from ..models import UserRole, Permission, UserAuditLog, UserPreference
from ..forms import (
    CreateUserForm, CustomUserCreationForm, CustomUserChangeForm,
    UserRoleForm, PermissionForm, UserPreferenceForm, BulkPermissionForm,
    UserSearchForm, AuditLogFilterForm
)
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class CreateUserFormTest(TestCase):
    """Test cases for the CreateUserForm"""
    def test_create_user_form_widgets_and_help_texts(self):
        """Test create user form widgets and help texts"""
        form = CreateUserForm()
        self.assertIn('Select the user role', str(form.fields['role'].help_text))
        self.assertIn('Department or organizational unit', str(form.fields['department'].help_text))
        self.assertIn('Specific laboratory unit', str(form.fields['lab_unit'].help_text))
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
        self.assertIn('role', form.fields)
        self.assertIn('department', form.fields)
        self.assertIn('lab_unit', form.fields)
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
        form_data = {
            'permission_type': 'edit',
            'content_type': self.content_type.id,
            'object_id': self.sample.id,
            'expires_at': ''
        }
        form = PermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
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
        self.assertIn('Select the user to grant permission to', str(form.fields['user'].help_text))
        self.assertIn('Type of permission to grant', str(form.fields['permission_type'].help_text))
        self.assertIn('Optional expiration date', str(form.fields['expires_at'].help_text))
        self.assertIn('form-control', form.fields['user'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['permission_type'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['expires_at'].widget.attrs['class'])


class UserPreferenceFormTest(TestCase):
    """Test cases for the UserPreferenceForm"""
    def test_user_preference_form_widgets_and_help_texts(self):
        """Test user preference form widgets and help texts"""
        form = UserPreferenceForm()
        self.assertIn('dark_mode', form.fields)
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
        form_data = {
            'permission_type': 'view',
            'content_type': content_type.id,
            'object_id': 1,
            'expires_at': ''
        }
        form = BulkPermissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('users', form.errors)
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
        self.assertIn('Select users to grant permissions to', str(form.fields['users'].help_text))
        self.assertIn('Type of permission to grant', str(form.fields['permission_type'].help_text))
        self.assertIn('Optional expiration date', str(form.fields['expires_at'].help_text))
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
        self.assertIn('form-control', form.fields['search'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['role'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['department'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['is_active'].widget.attrs['class'])
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
        self.assertIn('form-control', form.fields['user'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['action'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['target_type'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['date_from'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['date_to'].widget.attrs['class'])
        self.assertIn('Filter by target type...', form.fields['target_type'].widget.attrs['placeholder'])
