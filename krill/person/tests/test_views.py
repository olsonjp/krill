import unittest.mock as mock
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

from ..models import UserRole, Permission, UserAuditLog, UserPreference
from ..forms import (
    CreateUserForm, UserRoleForm, PermissionForm, BulkPermissionForm,
    UserSearchForm, AuditLogFilterForm
)
from ..views import DataImportView
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class PersonViewTest(TestCase):
    """Base test class for person views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.factory = RequestFactory()
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        self.viewer_role = self.viewer_user.role
        self.viewer_role.role = 'viewer'
        self.viewer_role.save()
        self.lab_member_user = User.objects.create_user(
            username='lab_member',
            email='lab_member@example.com',
            password='testpass123'
        )
        self.lab_member_role = self.lab_member_user.role
        self.lab_member_role.role = 'lab_member'
        self.lab_member_role.save()
        self.lab_manager_user = User.objects.create_user(
            username='lab_manager',
            email='lab_manager@example.com',
            password='testpass123'
        )
        self.lab_manager_role = self.lab_manager_user.role
        self.lab_manager_role.role = 'lab_manager'
        self.lab_manager_role.save()
        self.lab_admin_user = User.objects.create_user(
            username='lab_admin',
            email='lab_admin@example.com',
            password='testpass123'
        )
        self.lab_admin_role = self.lab_admin_user.role
        self.lab_admin_role.role = 'lab_admin'
        self.lab_admin_role.save()
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
        self.assertEqual(response.status_code, 302)
    def test_toggle_theme_requires_post(self):
        """Test that toggle_theme only accepts POST requests"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 405)
    def test_toggle_theme_creates_preference(self):
        """Test that toggle_theme creates user preference if it doesn't exist"""
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        preference = UserPreference.objects.get(user=self.viewer_user)
        self.assertTrue(preference.dark_mode)
    def test_toggle_theme_toggles_existing_preference(self):
        """Test that toggle_theme toggles existing preference"""
        preference = self.viewer_user.preference
        preference.dark_mode = False
        preference.save()
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:toggle_theme'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        preference.refresh_from_db()
        self.assertTrue(preference.dark_mode)


class CreateUserViewTest(PersonViewTest):
    """Test cases for the create_user view"""
    def test_create_user_requires_lab_manager_role(self):
        """Test that create_user requires lab_manager role or higher"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:create_user'))
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:user_detail', kwargs={'user_id': User.objects.get(username='newuser').id}))
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
        self.assertTrue(hasattr(new_user, 'role'))
        self.assertEqual(new_user.role.role, 'lab_member')
        self.assertEqual(new_user.role.department, 'Research')
        self.assertEqual(new_user.role.lab_unit, 'Lab A')
        self.assertTrue(hasattr(new_user, 'preference'))
        self.assertFalse(new_user.preference.dark_mode)
        audit_log = UserAuditLog.objects.filter(
            user=self.lab_admin_user,
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
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'role': 'lab_member'
        }
        response = self.client.post(reverse('person:create_user'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'person/create_user.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())


class UserListViewTest(PersonViewTest):
    """Test cases for the user_list view"""
    def test_user_list_requires_lab_admin_role(self):
        """Test that user_list requires lab_admin role"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 200)
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
        response = self.client.get(reverse('person:user_list'), {'search': 'lab_manager'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        response = self.client.get(reverse('person:user_list'), {'role': 'lab_manager'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:user_list'), {'department': 'Research'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:user_list'), {'is_active': 'True'})
        self.assertEqual(response.status_code, 200)


class UserDetailViewTest(PersonViewTest):
    """Test cases for the user_detail view"""
    def test_user_detail_requires_lab_admin_role(self):
        """Test that user_detail requires lab_admin role"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 404)


class UserRoleEditViewTest(PersonViewTest):
    """Test cases for the user_role_edit view"""
    def test_user_role_edit_requires_lab_manager_role(self):
        """Test that user_role_edit requires lab_manager role"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.lab_member_role.refresh_from_db()
        self.assertEqual(self.lab_member_role.role, 'lab_manager')
        self.assertEqual(self.lab_member_role.department, 'Updated Research')
        self.assertEqual(self.lab_member_role.lab_unit, 'Lab B')
        audit_log = UserAuditLog.objects.filter(
            user=self.lab_admin_user,
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
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:permission_list'))
        self.assertEqual(response.status_code, 200)
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
        response = self.client.get(reverse('person:permission_list'), {'user': 'lab_member'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:permission_list'), {'permission_type': 'view'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:permission_list'), {'content_type': 'sample'})
        self.assertEqual(response.status_code, 200)


class GrantPermissionViewTest(PersonViewTest):
    """Test cases for the grant_permission view"""
    def test_grant_permission_requires_lab_manager_role(self):
        """Test that grant_permission requires lab_manager role"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:grant_permission'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:grant_permission'))
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:permission_list'))
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
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:bulk_grant_permission'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:bulk_grant_permission'))
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('person:permission_list'))
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
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)
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
        response = self.client.get(reverse('person:audit_log'), {'user': self.lab_member_user.id})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:audit_log'), {'action': 'create'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('person:audit_log'), {'target_type': 'User'})
        self.assertEqual(response.status_code, 200)


class UserPermissionsApiViewTest(PersonViewTest):
    """Test cases for the user_permissions_api view"""
    def test_user_permissions_api_requires_lab_manager_role(self):
        """Test that user_permissions_api requires lab_manager role"""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
    def test_user_permissions_api_get_request(self):
        """Test user_permissions_api GET request"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('user', data)
        self.assertIn('role_permissions', data)
        self.assertIn('object_permissions', data)
        self.assertEqual(data['user']['id'], self.lab_member_user.id)
        self.assertEqual(data['user']['username'], 'lab_member')
        self.assertEqual(data['user']['role'], 'lab_member')
    def test_user_permissions_api_nonexistent_user(self):
        """Test user_permissions_api with nonexistent user"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': 99999}))
        self.assertEqual(response.status_code, 404)


class GrantObjectPermissionApiViewTest(PersonViewTest):
    """Test cases for the grant_object_permission_api view"""
    def test_grant_object_permission_api_requires_lab_manager_role(self):
        """Test that grant_object_permission_api requires lab_manager role"""
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 400)
    def test_grant_object_permission_api_requires_post(self):
        """Test that grant_object_permission_api only accepts POST requests"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 405)
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
        self.client.force_login(self.viewer_user)
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.lab_admin_user)
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 400)
    def test_revoke_object_permission_api_requires_post(self):
        """Test that revoke_object_permission_api only accepts POST requests"""
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 405)
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
        self.test_csv_content = """Cell Line;Source;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Number of Aliquots Total;Disposition;Sample Notes;Aliquot Notes;Aliquot/SubA Passage#;Experiment #
MDA MB 134VI (MM134);UPMC/MJS;Sikora LN2 #1;4;F;1;1;Cells;5;In Storage;Legacy MM134 from Oesterreich Lab banks;;p+33;EXP001
MDA MB 134VI (MM134);UPMC/MJS;Sikora LN2 #1;4;F;1;2;Cells;3;Checked Out;Legacy MM134 from Oesterreich Lab banks;Thawed by MTS on 09.04.19;p+33;EXP001"""

    def test_data_import_requires_lab_manager_role(self):
        """Test that data import requires lab_manager role or higher"""
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:data_import'))
        self.assertEqual(response.status_code, 200)

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

        preview_data = response.context['preview_data']
        self.assertIn('sources', preview_data)
        self.assertIn('samples', preview_data)
        self.assertIn('aliquots', preview_data)

    def test_data_import_form_validation(self):
        """Test data import form validation"""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

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

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(self.test_csv_content)
            temp_file_path = temp_file.name

        try:
            view = DataImportView()
            fixtures = view.convert_csv_to_fixtures(temp_file_path)

            self.assertIsInstance(fixtures, list)
            self.assertGreater(len(fixtures), 0)

            fixture_models = [fixture['model'] for fixture in fixtures]
            self.assertIn('sample.source', fixture_models)
            self.assertIn('sample.sample', fixture_models)
            self.assertIn('sample.aliquot', fixture_models)
            self.assertNotIn('sample.aliquottube', fixture_models)
            self.assertIn('storage.site', fixture_models)
            self.assertIn('storage.device', fixture_models)
            self.assertIn('storage.shelf', fixture_models)
            self.assertIn('storage.rack', fixture_models)
            self.assertIn('storage.box', fixture_models)
            self.assertIn('sample.aliquotlocation', fixture_models)

            storage_fixtures = {f['model']: f for f in fixtures if f['model'].startswith('storage.')}

            self.assertIn('storage.site', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.site']['fields']['name'], 'Default Site')

            self.assertIn('storage.device', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.device']['fields']['name'], 'Sikora LN2 #1')

            self.assertIn('storage.shelf', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.shelf']['fields']['name'], 'F')

            self.assertIn('storage.rack', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.rack']['fields']['name'], '4')

            self.assertIn('storage.box', storage_fixtures)
            self.assertEqual(storage_fixtures['storage.box']['fields']['name'], '4_F')

            location_fixtures = [f for f in fixtures if f['model'] == 'sample.aliquotlocation']
            self.assertGreater(len(location_fixtures), 0)
            for location in location_fixtures:
                self.assertEqual(location['fields']['row'], 1)
                self.assertIn(location['fields']['column'], [1, 2])

            aliquot_fixtures = [f for f in fixtures if f['model'] == 'sample.aliquot']
            # CSV has 5 + 3 = 8 aliquots (one record per physical item)
            self.assertEqual(len(aliquot_fixtures), 8)

            for aliquot in aliquot_fixtures:
                disposition_pk = aliquot['fields']['disposition']
                disposition_fixture = next(f for f in fixtures if f['model'] == 'sample.aliquotdisposition' and f['pk'] == disposition_pk)
                self.assertIn(disposition_fixture['fields']['disposition_type'], ['stored', 'in_use', 'exhausted'])

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_data_import_proceed_with_import_requires_import_id(self):
        """Proceed with Import path: missing import_id redirects with error (no form validation)."""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        response = self.client.post(
            reverse('person:data_import'),
            {'proceed_with_import': '1'},
            follow=True,
        )
        self.assertContains(response, 'Import session expired', status_code=200)

    def test_data_import_proceed_with_import_invalid_import_id_redirects_with_error(self):
        """Proceed with Import path: invalid/non-existent import_id redirects with error."""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        response = self.client.post(
            reverse('person:data_import'),
            {'proceed_with_import': '1', 'import_id': 'nonexistent-uuid-12345'},
            follow=True,
        )
        self.assertContains(response, 'Import file not found', status_code=200)

    def test_data_import_preview_cleanup_on_error(self):
        """When preview fails after store_temp_file, cleanup_temp_file is called (regression)."""
        self.lab_manager_user.is_staff = True
        self.lab_manager_user.save()
        self.client.force_login(self.lab_admin_user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile(
            "test.csv",
            self.test_csv_content.encode('utf-8'),
            content_type="text/csv",
        )

        fake_import_id = "test-import-id-12345"
        with mock.patch.object(
            DataImportView, 'store_temp_file', return_value=fake_import_id
        ), mock.patch.object(
            DataImportView, 'preview_import', side_effect=Exception("preview failed")
        ), mock.patch.object(
            DataImportView, 'cleanup_temp_file', wraps=lambda *a, **k: None
        ) as cleanup_mock:
            response = self.client.post(
                reverse('person:data_import'),
                {'csv_file': csv_file},
            )
            cleanup_mock.assert_called_once_with(fake_import_id, self.lab_admin_user.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)

    def _csv_fixtures_from_bytes(self, raw_bytes):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            f.write(raw_bytes)
            path = f.name
        try:
            return DataImportView().convert_csv_to_fixtures(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_convert_csv_handles_utf8_bom(self):
        """UTF-8 BOM prefix must not corrupt the first column name."""
        raw = b'\xef\xbb\xbf' + self.test_csv_content.encode('utf-8')
        fixtures = self._csv_fixtures_from_bytes(raw)
        sources = [f for f in fixtures if f['model'] == 'sample.source']
        self.assertGreater(len(sources), 0)

    def test_convert_csv_handles_comma_delimiter(self):
        """Comma-delimited CSV is parsed correctly via auto-detection."""
        comma_content = self.test_csv_content.replace(';', ',')
        fixtures = self._csv_fixtures_from_bytes(comma_content.encode('utf-8'))
        sources = [f for f in fixtures if f['model'] == 'sample.source']
        self.assertGreater(len(sources), 0)

    def test_convert_csv_handles_tab_delimiter(self):
        """Tab-delimited CSV is parsed correctly via auto-detection."""
        tab_content = self.test_csv_content.replace(';', '\t')
        fixtures = self._csv_fixtures_from_bytes(tab_content.encode('utf-8'))
        sources = [f for f in fixtures if f['model'] == 'sample.source']
        self.assertGreater(len(sources), 0)

    def test_convert_csv_missing_required_columns_gives_helpful_error(self):
        """Missing required columns raise an error that names both missing and found columns."""
        bad_csv = b'Name;Value\nTest;123\n'
        with self.assertRaises(Exception) as cm:
            self._csv_fixtures_from_bytes(bad_csv)
        msg = str(cm.exception)
        self.assertIn('Source', msg)
        self.assertIn('Name', msg)
