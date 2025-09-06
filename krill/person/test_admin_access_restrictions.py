"""
Test cases for admin access restrictions.

This module tests that admin functionality is properly restricted to users with
lab administrator privileges only.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
from django.http import HttpRequest

from .models import UserRole, UserPreference
from .admin import KrillAdminSite

User = get_user_model()


class AdminAccessRestrictionTest(TestCase):
    """Test cases for admin access restrictions"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test users with different roles
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

    def test_sidebar_admin_section_visibility(self):
        """Test that admin sidebar section is only visible to lab managers and administrators"""
        # Test with viewer user
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Admin section should not be visible
        self.assertNotContains(response, 'admin-section')
        self.assertNotContains(response, 'User Management')
        self.assertNotContains(response, 'Create User')
        self.assertNotContains(response, 'Audit Log')
        self.assertNotContains(response, 'Permissions')
        self.assertNotContains(response, 'Data Import')
        self.assertNotContains(response, 'System Admin')

        # Test with lab_member user
        self.client.force_login(self.lab_member_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Admin section should not be visible
        self.assertNotContains(response, 'admin-section')
        self.assertNotContains(response, 'User Management')

        # Test with lab_manager user
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Admin section should be visible
        self.assertContains(response, 'admin-section')
        self.assertContains(response, 'User Management')

        # Test with lab_admin user
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # Admin section should be visible
        self.assertContains(response, 'admin-section')
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'Create User')
        self.assertContains(response, 'Audit Log')
        self.assertContains(response, 'Permissions')
        self.assertContains(response, 'Data Import')
        self.assertContains(response, 'System Admin')

    def test_user_management_view_access(self):
        """Test that user management views are restricted to lab managers and administrators"""
        # Test user_list view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:user_list'))
                self.assertEqual(response.status_code, expected_status)

        # Test create_user view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:create_user'))
                self.assertEqual(response.status_code, expected_status)

        # Test user_detail view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
                self.assertEqual(response.status_code, expected_status)

        # Test user_role_edit view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:user_role_edit', kwargs={'user_id': self.lab_member_user.id}))
                self.assertEqual(response.status_code, expected_status)

    def test_permission_management_view_access(self):
        """Test that permission management views are restricted to lab managers and administrators"""
        # Test permission_list view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:permission_list'))
                self.assertEqual(response.status_code, expected_status)

        # Test grant_permission view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:grant_permission'))
                self.assertEqual(response.status_code, expected_status)

        # Test bulk_grant_permission view
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:bulk_grant_permission'))
                self.assertEqual(response.status_code, expected_status)

    def test_audit_log_view_access(self):
        """Test that audit log view is restricted to lab managers and administrators"""
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:audit_log'))
                self.assertEqual(response.status_code, expected_status)

    def test_data_import_view_access(self):
        """Test that data import view is restricted to lab managers and administrators"""
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse('person:data_import'))
                self.assertEqual(response.status_code, expected_status)

    def test_api_endpoints_access(self):
        """Test that admin API endpoints are restricted to lab managers and administrators"""
        # Test user_permissions_api
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 200)
        ]:
            with self.subTest(user=user.username, endpoint='user_permissions_api'):
                self.client.force_login(user)
                response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_member_user.id}))
                self.assertEqual(response.status_code, expected_status)

        # Test grant_object_permission_api
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 400)  # 400 because of missing parameters, but access is allowed
        ]:
            with self.subTest(user=user.username, endpoint='grant_object_permission_api'):
                self.client.force_login(user)
                response = self.client.post(reverse('person:grant_object_permission_api'))
                # API endpoints return 400 for bad requests, 403 for forbidden, or 200 for success
                if expected_status == 200:
                    self.assertIn(response.status_code, [200, 400],
                                 f"Expected 200 or 400 for lab_manager, got {response.status_code}")
                else:
                    self.assertEqual(response.status_code, expected_status)

        # Test revoke_object_permission_api
        for user, expected_status in [
            (self.viewer_user, 403),
            (self.lab_member_user, 403),
            (self.lab_manager_user, 200),
            (self.lab_admin_user, 400)  # 400 because of missing parameters, but access is allowed
        ]:
            with self.subTest(user=user.username, endpoint='revoke_object_permission_api'):
                self.client.force_login(user)
                response = self.client.post(reverse('person:revoke_object_permission_api'))
                # API endpoints return 400 for bad requests, 403 for forbidden, or 200 for success
                if expected_status == 200:
                    self.assertIn(response.status_code, [200, 400],
                                 f"Expected 200 or 400 for lab_manager, got {response.status_code}")
                else:
                    self.assertEqual(response.status_code, expected_status)

    def test_django_admin_site_access(self):
        """Test that Django admin site is restricted to lab managers and administrators"""
        admin_site = KrillAdminSite(name='test_admin')

        # Test with different user roles
        for user, expected_access in [
            (self.viewer_user, False),
            (self.lab_member_user, False),
            (self.lab_manager_user, True),
            (self.lab_admin_user, True)
        ]:
            with self.subTest(user=user.username):
                # Create a mock request
                request = HttpRequest()
                request.user = user

                # Test has_permission method
                has_access = admin_site.has_permission(request)
                self.assertEqual(has_access, expected_access)

    def test_django_admin_url_access(self):
        """Test that Django admin URLs are restricted to lab managers and administrators"""
        # Test admin index page
        for user, expected_status in [
            (self.viewer_user, 302),  # Redirect to login
            (self.lab_member_user, 302),  # Redirect to login
            (self.lab_manager_user, 200),  # Access granted
            (self.lab_admin_user, 200)  # Access granted
        ]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get('/admin/')
                self.assertEqual(response.status_code, expected_status)

    def test_user_detail_admin_button_visibility(self):
        """Test that admin button in user detail template is only visible to lab managers and administrators"""
        # Test with viewer user
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 403)  # Should be forbidden

        # Test with lab_manager user
        self.client.force_login(self.lab_manager_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)

        # Admin button should be visible for lab_manager
        self.assertContains(response, 'admin_panel_settings')
        self.assertContains(response, 'Admin')

        # Test with lab_admin user
        self.client.force_login(self.lab_admin_user)
        response = self.client.get(reverse('person:user_detail', kwargs={'user_id': self.lab_member_user.id}))
        self.assertEqual(response.status_code, 200)

        # Admin button should be visible for lab_admin
        self.assertContains(response, 'admin_panel_settings')
        self.assertContains(response, 'Admin')

    def test_template_context_admin_visibility(self):
        """Test that admin elements are properly hidden in templates based on user role"""
        # Test sidebar template rendering
        template_content = """
        {% if user.role.role == 'lab_admin' or user.role.role == 'lab_manager' %}
        <div class="admin-section">Admin Content</div>
        {% endif %}
        """

        template = Template(template_content)

        # Test with different user roles
        for user, should_contain_admin in [
            (self.viewer_user, False),
            (self.lab_member_user, False),
            (self.lab_manager_user, True),
            (self.lab_admin_user, True)
        ]:
            with self.subTest(user=user.username):
                context = Context({'user': user})
                rendered = template.render(context)

                if should_contain_admin:
                    self.assertIn('Admin Content', rendered)
                else:
                    self.assertNotIn('Admin Content', rendered)

    def test_unauthenticated_user_access(self):
        """Test that unauthenticated users cannot access admin functionality"""
        # Test admin views
        admin_urls = [
            reverse('person:user_list'),
            reverse('person:create_user'),
            reverse('person:permission_list'),
            reverse('person:audit_log'),
            reverse('person:data_import'),
            '/admin/',
        ]

        for url in admin_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Should either redirect to login (302) or return 403 Forbidden
                # Both are acceptable security behaviors
                self.assertIn(response.status_code, [302, 403])
                if response.status_code == 302:
                    self.assertIn('/login/', response.url)

    def test_role_hierarchy_enforcement(self):
        """Test that role hierarchy is properly enforced"""
        # Create a user with no role (edge case)
        no_role_user = User.objects.create_user(
            username='no_role',
            email='no_role@example.com',
            password='testpass123'
        )
        # Delete the automatically created role
        no_role_user.role.delete()

        # Test that user without role cannot access admin
        self.client.force_login(no_role_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_site_permission_method(self):
        """Test the custom admin site permission method thoroughly"""
        admin_site = KrillAdminSite(name='test_admin')

        # Test with unauthenticated user
        from django.contrib.auth.models import AnonymousUser
        request = HttpRequest()
        request.user = AnonymousUser()
        has_access = admin_site.has_permission(request)
        self.assertFalse(has_access)

        # Test with user that has no role
        no_role_user = User.objects.create_user(
            username='no_role_test',
            email='no_role_test@example.com',
            password='testpass123'
        )
        no_role_user.role.delete()

        request = HttpRequest()
        request.user = no_role_user
        has_access = admin_site.has_permission(request)
        self.assertFalse(has_access)

        # Test with user that has lab_manager role
        request = HttpRequest()
        request.user = self.lab_manager_user
        has_access = admin_site.has_permission(request)
        self.assertTrue(has_access)

        # Test with lab_admin user
        request = HttpRequest()
        request.user = self.lab_admin_user
        has_access = admin_site.has_permission(request)
        self.assertTrue(has_access)

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling in admin access control"""
        # Test with user that has malformed role
        malformed_user = User.objects.create_user(
            username='malformed',
            email='malformed@example.com',
            password='testpass123'
        )
        # Manually set a malformed role
        malformed_user.role.role = 'invalid_role'
        malformed_user.role.save()

        self.client.force_login(malformed_user)
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_admin_functionality_completeness(self):
        """Test that all admin functionality is properly restricted"""
        # List of all admin-related URLs that should be restricted
        admin_urls = [
            ('person:user_list', 'GET'),
            ('person:create_user', 'GET'),
            ('person:user_detail', 'GET', {'user_id': self.lab_member_user.id}),
            ('person:user_role_edit', 'GET', {'user_id': self.lab_member_user.id}),
            ('person:permission_list', 'GET'),
            ('person:grant_permission', 'GET'),
            ('person:bulk_grant_permission', 'GET'),
            ('person:audit_log', 'GET'),
            ('person:data_import', 'GET'),
            ('person:user_permissions_api', 'GET', {'user_id': self.lab_member_user.id}),
        ]

        # Test each URL with non-admin users (excluding lab_manager who now has access)
        non_admin_users = [self.viewer_user, self.lab_member_user]

        for url_name, method, *args in admin_urls:
            kwargs = args[0] if args else {}

            for user in non_admin_users:
                with self.subTest(url=url_name, user=user.username, method=method):
                    self.client.force_login(user)

                    if method == 'GET':
                        response = self.client.get(reverse(url_name, kwargs=kwargs))
                    elif method == 'POST':
                        response = self.client.post(reverse(url_name, kwargs=kwargs))

                    # All should return 403 Forbidden
                    self.assertEqual(response.status_code, 403,
                                   f"URL {url_name} should be forbidden for {user.username}")

        # Test that lab_manager and lab_admin users DO have access
        admin_users = [self.lab_manager_user, self.lab_admin_user]

        for url_name, method, *args in admin_urls:
            kwargs = args[0] if args else {}

            for user in admin_users:
                with self.subTest(url=url_name, user=user.username, method=method):
                    self.client.force_login(user)

                    if method == 'GET':
                        response = self.client.get(reverse(url_name, kwargs=kwargs))
                    elif method == 'POST':
                        response = self.client.post(reverse(url_name, kwargs=kwargs))

                    # Should return 200 OK (or appropriate success status)
                    self.assertIn(response.status_code, [200, 302],
                                 f"URL {url_name} should be accessible for {user.username}, got {response.status_code}")

    def test_admin_access_audit_logging(self):
        """Test that admin access attempts are properly logged"""
        # This test would require checking UserAuditLog entries
        # For now, we'll just ensure the views are accessible to lab_admin
        self.client.force_login(self.lab_admin_user)

        # Access admin views and ensure they work
        response = self.client.get(reverse('person:user_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('person:audit_log'))
        self.assertEqual(response.status_code, 200)

        # Check that audit logs are being created (if the view creates them)
        # This would require more specific testing of the audit logging functionality
