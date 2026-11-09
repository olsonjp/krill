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

    def test_convert_csv_headers_are_case_insensitive(self):
        """Header case and surrounding whitespace must not matter."""
        header, rest = self.test_csv_content.split('\n', 1)
        mangled = ';'.join(
            (' ' + h.lower() + ' ') if i % 2 else h.upper()
            for i, h in enumerate(header.split(';'))
        )
        expected = self._csv_fixtures_from_bytes(self.test_csv_content.encode('utf-8'))
        actual = self._csv_fixtures_from_bytes((mangled + '\n' + rest).encode('utf-8'))
        self.assertGreater(len(actual), 0)
        self.assertEqual(self._strip_timestamps(actual), self._strip_timestamps(expected))

    @staticmethod
    def _strip_timestamps(fixtures):
        skip = {'created_at', 'updated_at'}
        return [
            {**f, 'fields': {k: v for k, v in f['fields'].items() if k not in skip}}
            for f in fixtures
        ]

    def _xlsx_bytes(self, rows, extra_sheet=True):
        """Build an in-memory XLSX with `rows` on the first sheet."""
        import io
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'All canes'
        for row in rows:
            ws.append(row)
        if extra_sheet:
            wb.create_sheet('Ignored').append(['not', 'the', 'data'])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _xlsx_rows(self):
        """XLSX equivalent of test_csv_content with Excel-typical cell types."""
        import datetime
        header = [h.lower() for h in self.test_csv_content.split('\n', 1)[0].split(';')] + ['Sample date']
        base = [
            ['MDA MB 134VI (MM134)', 'UPMC/MJS', 'Sikora LN2 #1', 4, 'F', 1.0, 1, 'Cells', 5, 'In Storage',
             'Legacy MM134 from Oesterreich Lab banks', None, 'p+33', 'EXP001', datetime.datetime(2021, 11, 1)],
            [],
            ['MDA MB 134VI (MM134)', 'UPMC/MJS', 'Sikora LN2 #1', 4, 'F', 1, 2.0, 'Cells', 3, 'Checked Out',
             'Legacy MM134 from Oesterreich Lab banks', 'Thawed by MTS on 09.04.19', 'p+33', 'EXP001', '7/2021'],
        ]
        return [header] + base

    def test_convert_xlsx_matches_equivalent_csv(self):
        """An XLSX upload yields the same fixtures as the equivalent CSV."""
        header, first, second = self.test_csv_content.split('\n')
        csv_equivalent = '\n'.join([header + ';Sample date', first + ';2021-11-01', second + ';7/2021'])
        expected = self._csv_fixtures_from_bytes(csv_equivalent.encode('utf-8'))
        actual = self._csv_fixtures_from_bytes(self._xlsx_bytes(self._xlsx_rows()))
        self.assertGreater(len(actual), 0)
        self.assertEqual(self._strip_timestamps(actual), self._strip_timestamps(expected))

    def test_convert_xlsx_preserves_multiline_cells(self):
        """Newlines inside a cell survive the XLSX conversion."""
        rows = self._xlsx_rows()
        rows[1][10] = 'Line one\nLine two'
        fixtures = self._csv_fixtures_from_bytes(self._xlsx_bytes(rows))
        notes = [f['fields'].get('notes', '') for f in fixtures if f['model'] == 'sample.sample']
        self.assertTrue(any('Line one\nLine two' in n for n in notes))

    def test_convert_xlsx_missing_column_still_reported(self):
        rows = self._xlsx_rows()
        rows[0][rows[0].index('disposition')] = 'status'
        with self.assertRaises(KeyError):
            self._csv_fixtures_from_bytes(self._xlsx_bytes(rows))

    def test_location_only_rows_are_skipped(self):
        """Rows with only a location and aliquot type (empty grid slots) are not imported."""
        header = 'Cell Line;Source;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Disposition;Sample Notes;Experiment #;Passage Number;Lab Member'
        content = '\n'.join([
            header,
            'HeLa;Lab A;Freezer 1;1;A;1;1;Cells;;;;p3;JS',
            ';;Freezer 1;1;A;1;2;Cells;;;;;',        # empty slot -> skipped
            ';;Freezer 1;1;A;1;3;Cells;;;;;',        # empty slot -> skipped
            ';;Freezer 1;1;A;1;4;Cells;;;;p13;MEM',  # no cell line but has passage/lab member -> kept
        ])
        view = DataImportView()
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            f.write(content)
        try:
            fixtures = view.convert_csv_to_fixtures(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(len([x for x in fixtures if x['model'] == 'sample.aliquot']), 2)
        self.assertEqual(len([x for x in fixtures if x['model'] == 'sample.aliquotlocation']), 2)
        self.assertEqual(view.skipped_empty_rows, 2)

    def test_note_rows_are_skipped(self):
        """A comment row with no cell line and no location is not imported as a tube."""
        from person.views import is_note_row
        self.assertTrue(is_note_row({'Cell Line': '', 'Experiment #': 'COMPLETE BOX H MISSING', 'Position 1': ''}))
        self.assertFalse(is_note_row({'Cell Line': 'HeLa', 'Position 1': ''}))   # unlocated tube is kept
        self.assertFalse(is_note_row({'Cell Line': '', 'Position 1': '1'}))
        import tempfile, os
        header = 'Cell Line;Source;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Disposition;Sample Notes;Experiment #'
        content = '\n'.join([header, 'HeLa;Lab A;Freezer 1;1;A;1;1;Cells;;;', ';;;;;;;;;;COMPLETE BOX H MISSING'])
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            f.write(content)
        view = DataImportView()
        try:
            fixtures = view.convert_csv_to_fixtures(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(len([x for x in fixtures if x['model'] == 'sample.aliquot']), 1)
        self.assertFalse([x for x in fixtures if x['model'] == 'storage.site' and x['fields']['name'] == 'Default Site'][1:])
        self.assertEqual(view.skipped_empty_rows, 1)

    def test_parse_sample_date(self):
        from datetime import date
        from person.views import parse_sample_date
        cases = {
            '': (None, True),
            '  ': (None, True),
            '2019-11-01': (date(2019, 11, 1), True),
            '2019-11-01 00:00:00': (date(2019, 11, 1), True),
            '11/2021': (date(2021, 11, 1), True),      # month only -> 1st
            '7/2021': (date(2021, 7, 1), True),
            'Jul-21': (date(2021, 7, 1), True),
            '12/26/2020': (date(2020, 12, 26), True),
            '12/26/20': (date(2020, 12, 26), True),
            '2/29/25': (None, False),                  # not a real date
            '4/38/23': (None, False),
            '2025': (None, False),
            "'2025'": (None, False),
            '25-Jul': (None, False),                   # ambiguous: left blank, not guessed
            'garbage': (None, False),
        }
        for text, expected in cases.items():
            self.assertEqual(parse_sample_date(text), expected, text)

    def test_import_reads_passage_lab_member_and_date(self):
        import tempfile, os
        header = 'Cell Line;Source;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Disposition;Sample Notes;Experiment #;Passage Number;Lab Member;Sample date '
        content = '\n'.join([
            header,
            'HeLa;Lab A;Freezer 1;1;A;1;1;Cells;;;;p3;JS;2019-11-01',
            'HeLa;Lab A;Freezer 1;1;A;1;2;Cells;;;;p20EV p39+4-5;MS;7/2021',
            'HeLa;Lab A;Freezer 1;1;A;1;3;Cells;;;;;;4/38/23',
        ])
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            f.write(content)
        view = DataImportView()
        try:
            fixtures = view.convert_csv_to_fixtures(f.name)
        finally:
            os.unlink(f.name)
        aliquots = [x['fields'] for x in fixtures if x['model'] == 'sample.aliquot']
        self.assertEqual(
            [(a['passage'], a['lab_member_initials'], a['sample_date']) for a in aliquots],
            [('p3', 'JS', '2019-11-01'), ('p20EV p39+4-5', 'MS', '2021-07-01'), ('', '', None)],
        )
        self.assertEqual(view.unparsed_sample_dates, 1)

    def test_import_loads_new_fields_into_database(self):
        """The generated fixtures must be loadable (field names match the model)."""
        import json, tempfile, os
        from django.core.management import call_command
        from sample.models.aliquot import Aliquot
        fixtures = self._csv_fixtures_from_bytes(
            (self.test_csv_content.replace('Experiment #', 'Experiment #;Passage Number;Lab Member;Sample date', 1)
             .replace('EXP001', 'EXP001;p5;AB;3/2022')).encode('utf-8'))
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            json.dump(fixtures, f)
        try:
            call_command('loaddata', f.name, verbosity=0)
        finally:
            os.unlink(f.name)
        aliquot = Aliquot.objects.first()
        self.assertEqual((aliquot.passage, aliquot.lab_member_initials, str(aliquot.sample_date)), ('p5', 'AB', '2022-03-01'))

    def test_is_location_only_row(self):
        from person.views import is_location_only_row
        self.assertTrue(is_location_only_row({'Cell Line': '', 'Position 1': '1', 'Aliquot Type': 'Cells', 'Notes': ' '}))
        self.assertFalse(is_location_only_row({'Cell Line': 'HeLa', 'Position 1': '1'}))
        self.assertFalse(is_location_only_row({'Cell Line': '', 'Sample date': '2020-01-01'}))
        self.assertFalse(is_location_only_row({'Cell Line': '', None: ['stray']}))

    def test_preview_reports_skipped_rows(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        content = self.test_csv_content + '\n;;Sikora LN2 #1;4;F;5;5;Cells;;;;;;'
        upload = SimpleUploadedFile('x.csv', content.encode('utf-8'), content_type='text/csv')
        response = self.client.post(reverse('person:data_import'), {'csv_file': upload})
        self.assertEqual(response.context['preview_data']['skipped_rows'], 1)

    def test_xlsx_upload_through_preview(self):
        """Uploading an .xlsx through the import view produces a preview."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        upload = SimpleUploadedFile(
            'inventory.xlsx',
            self._xlsx_bytes(self._xlsx_rows()),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response = self.client.post(reverse('person:data_import'), {'csv_file': upload})
        self.assertEqual(response.status_code, 200)
        self.assertIn('preview_data', response.context)
        self.assertEqual(response.context['preview_data']['aliquots'], 8)

    def test_legacy_xls_upload_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        upload = SimpleUploadedFile('old.xls', b'\xd0\xcf\x11\xe0junk', content_type='application/vnd.ms-excel')
        response = self.client.post(reverse('person:data_import'), {'csv_file': upload})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('preview_data', response.context)
        self.assertIn('.xls', str(response.context['form'].errors))

    def test_convert_csv_missing_column_still_reported(self):
        """Case-insensitivity must not hide genuinely missing columns."""
        content = self.test_csv_content.replace('Disposition', 'Status')
        with self.assertRaises(KeyError):
            self._csv_fixtures_from_bytes(content.encode('utf-8'))

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

    def _disposition_csv(self, rows):
        """Build a minimal valid CSV with given (cell_line, disposition) rows."""
        header = "Cell Line;Source;Freezer Name;Position 1;Position 2;Aliquot Type;Number of Aliquots Total;Disposition;Sample Notes;Experiment #\n"
        body = "".join(f"{cl};Lab;FreezerA;1;A;Cells;1;{disp};;\n" for cl, disp in rows)
        return (header + body).encode('utf-8')

    def _disp_types_from_fixtures(self, fixtures):
        disp_map = {f['pk']: f['fields']['disposition_type'] for f in fixtures if f['model'] == 'sample.aliquotdisposition'}
        return {disp_map[a['fields']['disposition']] for a in fixtures if a['model'] == 'sample.aliquot'}

    def test_disposition_model_values_accepted_directly(self):
        """CSV using model disposition values (stored, in_use, exhausted, disposed) imports correctly."""
        fixtures = self._csv_fixtures_from_bytes(self._disposition_csv([
            ('SampleA', 'stored'), ('SampleB', 'in_use'),
            ('SampleC', 'exhausted'), ('SampleD', 'disposed'),
        ]))
        disp_types = self._disp_types_from_fixtures(fixtures)
        self.assertIn('stored', disp_types)
        self.assertIn('in_use', disp_types)
        self.assertIn('exhausted', disp_types)
        self.assertIn('disposed', disp_types)

    def test_disposition_legacy_aliases_still_accepted(self):
        """Legacy CSV aliases (In Storage, Checked Out, Used, Disposed) still import correctly."""
        fixtures = self._csv_fixtures_from_bytes(self._disposition_csv([
            ('SampleA', 'In Storage'), ('SampleB', 'Checked Out'),
            ('SampleC', 'Used'), ('SampleD', 'Disposed'),
        ]))
        disp_types = self._disp_types_from_fixtures(fixtures)
        self.assertIn('stored', disp_types)
        self.assertIn('in_use', disp_types)
        self.assertIn('exhausted', disp_types)
        self.assertIn('disposed', disp_types)

    def test_convert_csv_missing_required_columns_gives_helpful_error(self):
        """Missing required columns raise an error that names both missing and found columns."""
        bad_csv = b'Name;Value\nTest;123\n'
        with self.assertRaises(Exception) as cm:
            self._csv_fixtures_from_bytes(bad_csv)
        msg = str(cm.exception)
        self.assertIn('Source', msg)
        self.assertIn('Name', msg)


class ImportBuildsOnExistingDataTest(TestCase):
    """The importer must add to current data, never overwrite or duplicate it."""

    CSV = (
        'Cell Line;Source;Freezer Name;Site;Position 1;Position 2;Position 3;Position 4;'
        'Aliquot Type;Disposition;Sample Notes;Experiment #\n'
        'HeLa;Lab A;Freezer 1;Main;4;F;1;1;Cells;In Storage;;\n'
        'HeLa;Lab A;Freezer 1;Main;4;F;1;2;PDX;In Storage;;\n'
    )

    def setUp(self):
        from sample.models.source import Source
        from sample.models.sample import Sample
        from sample.models.aliquot import AliquotType, AliquotDisposition
        from storage.models.site import Site
        from storage.models.storage import Device, Shelf, Rack, Box
        # Existing data whose primary keys deliberately sit where a from-scratch import would write.
        self.lab_admin_user = User.objects.create_user(username='importer', password='x')
        self.lab_admin_user.role.role = 'lab_admin'
        self.lab_admin_user.role.save()
        self.source = Source.objects.create(pk=1, name='Lab A')
        self.type_cells = AliquotType.objects.create(pk=1, name='Cells')
        self.disp = AliquotDisposition.objects.create(pk=1, name='In Storage', disposition_type='stored')
        self.site = Site.objects.create(pk=1, name='Main')
        self.device = Device.objects.create(pk=1, name='Freezer 1', site=self.site)
        self.shelf = Shelf.objects.create(pk=1, name='F', device=self.device)
        self.rack = Rack.objects.create(pk=1, name='4', shelf=self.shelf)
        self.box = Box.objects.create(pk=1, name='4_F', rack=self.rack, rows=10, columns=10)
        self.sample = Sample.objects.create(pk=1, name='HeLa', source=self.source, notes='keep me')
        # An unrelated existing source/box that a from-scratch import would clobber.
        Source.objects.create(pk=2, name='Other Lab')

    def _convert(self, text):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            f.write(text)
        view = DataImportView()
        try:
            return view, view.convert_csv_to_fixtures(f.name)
        finally:
            os.unlink(f.name)

    def _load(self, fixtures):
        import json, tempfile, os
        from django.core.management import call_command
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            json.dump(fixtures, f)
        try:
            call_command('loaddata', f.name, verbosity=0)
        finally:
            os.unlink(f.name)

    def test_existing_records_are_reused_not_recreated(self):
        view, fixtures = self._convert(self.CSV)
        models = [f['model'] for f in fixtures]
        for reused in ('sample.source', 'sample.sample', 'storage.site', 'storage.device',
                       'storage.shelf', 'storage.rack', 'storage.box', 'sample.aliquotdisposition'):
            self.assertNotIn(reused, models, f'{reused} should be reused, not recreated')
        # Only the genuinely new aliquot type is created, numbered after the existing one.
        new_types = [f for f in fixtures if f['model'] == 'sample.aliquottype']
        self.assertEqual([(f['fields']['name'], f['pk']) for f in new_types], [('PDX', 2)])
        aliquots = [f['fields'] for f in fixtures if f['model'] == 'sample.aliquot']
        self.assertEqual({a['sample'] for a in aliquots}, {1})
        self.assertEqual({a['disposition'] for a in aliquots}, {1})
        self.assertEqual({l['fields']['box'] for l in fixtures if l['model'] == 'sample.aliquotlocation'}, {1})
        self.assertEqual(view.reused_counts['boxes'], 1)
        self.assertEqual(view.reused_counts['sources'], 1)

    def test_loading_does_not_change_existing_rows(self):
        from sample.models.source import Source
        from sample.models.sample import Sample
        from sample.models.aliquot import Aliquot, AliquotLocation, AliquotType
        from storage.models.storage import Box
        _, fixtures = self._convert(self.CSV)
        self._load(fixtures)
        self.assertEqual(Source.objects.get(pk=1).name, 'Lab A')
        self.assertEqual(Source.objects.get(pk=2).name, 'Other Lab')
        self.assertEqual(Sample.objects.get(pk=1).notes, 'keep me')
        self.assertEqual(Sample.objects.count(), 1)
        self.assertEqual(Box.objects.count(), 1)
        self.assertEqual(AliquotType.objects.count(), 2)
        self.assertEqual(Aliquot.objects.filter(sample_id=1).count(), 2)
        self.assertEqual(AliquotLocation.objects.filter(box_id=1).count(), 2)

    def test_new_storage_is_added_beside_existing(self):
        text = self.CSV.replace('Freezer 1', 'Freezer 2')   # a different freezer in the same site
        _, fixtures = self._convert(text)
        devices = [f for f in fixtures if f['model'] == 'storage.device']
        self.assertEqual([(d['fields']['name'], d['pk']) for d in devices], [('Freezer 2', 2)])
        self.assertEqual([f['pk'] for f in fixtures if f['model'] == 'storage.box'], [2])
        self._load(fixtures)
        from storage.models.storage import Box
        self.assertEqual(sorted(Box.objects.values_list('name', flat=True)), ['4_F', '4_F'])

    def test_second_import_of_same_positions_fails_clearly(self):
        from person.views import ImportConflictError
        _, fixtures = self._convert(self.CSV)
        self._load(fixtures)
        with self.assertRaises(ImportConflictError) as ctx:
            self._convert(self.CSV)
        self.assertIn('2 storage slot(s) cannot be used', str(ctx.exception))
        self.assertIn('nothing was changed', str(ctx.exception))
        self.assertIn('probably already been imported', str(ctx.exception))
        self.assertEqual(len(ctx.exception.conflicts), 2)
        first = ctx.exception.conflicts[0]
        self.assertEqual((first['box'], first['row'], first['column'], first['cell_line']), ('4_F', 1, 1, 'HeLa'))
        self.assertIn("already holds aliquot #", first['reason'])

    def test_duplicate_slot_within_the_file_fails_clearly(self):
        from person.views import ImportConflictError
        text = self.CSV.replace('1;2;PDX', '1;1;PDX')
        with self.assertRaises(ImportConflictError):
            self._convert(text)

    def test_preview_lists_matched_records(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        upload = SimpleUploadedFile('x.csv', self.CSV.replace('1;2;PDX', '1;3;PDX').encode('utf-8'), content_type='text/csv')
        response = self.client.post(reverse('person:data_import'), {'csv_file': upload})
        reused = dict((label, n) for label, n in response.context['preview_data']['reused'])
        self.assertEqual(reused.get('boxes'), 1)
        self.assertEqual(reused.get('sources'), 1)
        self.assertContains(response, 'Matched to existing records')

    def test_summarize_conflicts_groups_by_box_and_reason(self):
        from person.views import summarize_conflicts
        conflicts = (
            [{'box': '1_A', 'row': r, 'column': 1, 'cell_line': name, 'reason': 'x', 'existing_sample': name}
             for r, name in enumerate(['M41', 'M41', 'PEO1', 'A', 'B'], start=1)]
            + [{'box': '2_G', 'row': 1, 'column': 1, 'cell_line': 'MCF7', 'reason': 'y', 'existing_sample': None}]
        )
        summary = summarize_conflicts(conflicts)
        self.assertEqual(summary[0], {
            'box': '1_A', 'reason': 'Slot already holds an aliquot in Krill', 'count': 5,
            'cell_lines': 'M41, PEO1, A and 1 more',
        })
        self.assertEqual((summary[1]['box'], summary[1]['count'], summary[1]['reason']),
                         ('2_G', 1, 'Slot used by more than one row in this file'))

    def test_refused_duplicate_upload_shows_summary_and_offers_csv(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        _, fixtures = self._convert(self.CSV)
        self._load(fixtures)                                  # the file is already in Krill
        response = self.client.post(reverse('person:data_import'), {
            'csv_file': SimpleUploadedFile('x.csv', self.CSV.encode('utf-8'), content_type='text/csv')})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('preview_data', response.context)
        self.assertIn('nothing was changed', response.context['error'])
        self.assertEqual(response.context['conflict_total'], 2)
        self.assertEqual(response.context['conflict_summary'][0]['box'], '4_F')
        self.assertContains(response, 'Slot already holds an aliquot in Krill')
        self.assertContains(response, 'Download all 2 refused rows')
        # the download has every refused row with its reason
        download = self.client.get(reverse('person:data_import_refused', args=[response.context['refusals_token']]))
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment', download['Content-Disposition'])
        lines = b''.join(download.streaming_content).decode().strip().splitlines()
        self.assertEqual(lines[0], 'Box,Row,Column,Cell line,Why refused')
        self.assertEqual(len(lines), 3)
        self.assertIn('4_F,1,1,HeLa,Slot already holds aliquot #', lines[1])

    def test_refusal_download_rejects_bad_or_foreign_tokens(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.lab_admin_user)
        _, fixtures = self._convert(self.CSV)
        self._load(fixtures)
        response = self.client.post(reverse('person:data_import'), {
            'csv_file': SimpleUploadedFile('x.csv', self.CSV.encode('utf-8'), content_type='text/csv')})
        token = response.context['refusals_token']
        self.assertEqual(self.client.get(reverse('person:data_import_refused', args=['not-a-hex-token'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('person:data_import_refused', args=['0' * 32])).status_code, 404)
        other = User.objects.create_user(username='other', password='x')
        other.role.role = 'lab_admin'
        other.role.save()
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('person:data_import_refused', args=[token])).status_code, 404)
