from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.http import JsonResponse
import json

from sample.models.sample import Sample
from sample.models.aliquot import Aliquot, AliquotType, AliquotDisposition
from sample.models.source import Source
from storage.models.storage import Device, Box, Shelf, Rack
from storage.models.site import Site
from person.models import UserRole, Permission, UserPreference, UserAuditLog

User = get_user_model()


class APITestCase(TestCase):
    """Base test case for API testing with common setup"""
    def setUp(self):
        """Set up test data for API tests"""
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.lab_admin = User.objects.create_user(
            username='lab_admin',
            email='lab_admin@test.com',
            password='testpass123'
        )
        self.lab_manager = User.objects.create_user(
            username='lab_manager',
            email='lab_manager@test.com',
            password='testpass123'
        )
        self.researcher = User.objects.create_user(
            username='researcher',
            email='researcher@test.com',
            password='testpass123'
        )
        # Create user roles
        self.admin_role, _ = UserRole.objects.get_or_create(
            user=self.admin_user,
            defaults={
                'role': 'lab_admin',
                'department': 'Admin'
            }
        )
        # Update role if it already exists
        if not _:
            self.admin_role.role = 'lab_admin'
            self.admin_role.save()
        self.lab_admin_role, _ = UserRole.objects.get_or_create(
            user=self.lab_admin,
            defaults={
                'role': 'lab_admin',
                'department': 'Lab Admin'
            }
        )
        # Update role if it already exists
        if not _:
            self.lab_admin_role.role = 'lab_admin'
            self.lab_admin_role.save()
        self.lab_manager_role, _ = UserRole.objects.get_or_create(
            user=self.lab_manager,
            defaults={
                'role': 'lab_manager',
                'department': 'Lab Manager'
            }
        )
        # Update role if it already exists
        if not _:
            self.lab_manager_role.role = 'lab_manager'
            self.lab_manager_role.save()
        self.researcher_role, _ = UserRole.objects.get_or_create(
            user=self.researcher,
            defaults={
                'role': 'lab_member',
                'department': 'Research'
            }
        )
        # Update role if it already exists
        if not _:
            self.researcher_role.role = 'lab_member'
            self.researcher_role.save()
        # Create test data
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source,
            experiment="Test experiment"
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.aliquot_disposition = AliquotDisposition.objects.create(
            name="Test Disposition",
            dispositionType="stored"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquotType=self.aliquot_type,
            quantity=5
        )
        # Create storage hierarchy
        self.site = Site.objects.create(
            name="Test Site",
            description="A test site"
        )
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site,
            auto_store_enabled=True
        )
        # Create shelf and rack first
        self.shelf = Shelf.objects.create(
            name="Test Shelf",
            device=self.device
        )
        self.rack = Rack.objects.create(
            name="Test Rack",
            shelf=self.shelf
        )
        self.box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=8,
            columns=12
        )
        # Create client
        self.client = Client()


class DashboardStatsAPITest(APITestCase):
    """Test cases for dashboard statistics API"""
    def test_dashboard_stats_requires_login(self):
        """Test that dashboard stats API requires authentication"""
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_dashboard_stats_authenticated_user(self):
        """Test dashboard stats API for authenticated user"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('active_samples', data)
        self.assertIn('storage_usage', data)
        self.assertIn('recent_reports', data)
        self.assertIn('alerts', data)
    def test_dashboard_stats_data_accuracy(self):
        """Test that dashboard stats return accurate data"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('dashboard_stats'))
        data = json.loads(response.content)
        # Check that stats match actual data
        self.assertEqual(data['active_samples'], Sample.objects.count())
        self.assertEqual(data['storage_usage'], 0)  # No tubes stored yet
        self.assertEqual(data['total_slots'], self.box.rows * self.box.columns)


class ThemeToggleAPITest(APITestCase):
    """Test cases for theme toggle API"""
    def test_theme_toggle_requires_login(self):
        """Test that theme toggle API requires authentication"""
        response = self.client.post(reverse('toggle_theme'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_theme_toggle_requires_post(self):
        """Test that theme toggle API only accepts POST requests"""
        self.client.login(username='admin', password='testpass123')
        # GET request should fail
        response = self.client.get(reverse('toggle_theme'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_theme_toggle_creates_preference(self):
        """Test that theme toggle creates user preference if it doesn't exist"""
        self.client.login(username='admin', password='testpass123')
        # Ensure no preference exists
        UserPreference.objects.filter(user=self.admin_user).delete()
        response = self.client.post(reverse('toggle_theme'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        # Check that preference was created
        preference = UserPreference.objects.get(user=self.admin_user)
        self.assertTrue(preference.dark_mode)
    def test_theme_toggle_toggles_existing_preference(self):
        """Test that theme toggle toggles existing preference"""
        self.client.login(username='admin', password='testpass123')
        # Create preference with dark_mode=False
        preference, created = UserPreference.objects.get_or_create(
            user=self.admin_user,
            defaults={'dark_mode': False}
        )
        if not created:
            preference.dark_mode = False
            preference.save()
        response = self.client.post(reverse('toggle_theme'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['dark_mode'])
        # Check that preference was toggled
        preference.refresh_from_db()
        self.assertTrue(preference.dark_mode)
        # Toggle again
        response = self.client.post(reverse('toggle_theme'))
        data = json.loads(response.content)
        self.assertFalse(data['dark_mode'])
        preference.refresh_from_db()
        self.assertFalse(preference.dark_mode)


class UserPermissionsAPITest(APITestCase):
    """Test cases for user permissions API"""
    def test_user_permissions_requires_login(self):
        """Test that user permissions API requires authentication"""
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.admin_user.id}))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_user_permissions_requires_lab_manager_role(self):
        """Test that user permissions API requires lab_manager role or higher"""
        self.client.login(username='researcher', password='testpass123')
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.admin_user.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden
    def test_user_permissions_lab_manager_access(self):
        """Test that lab_manager can access user permissions API"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.admin_user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('user', data)
        self.assertIn('role_permissions', data)
        self.assertIn('object_permissions', data)
        # Check user data
        self.assertEqual(data['user']['id'], self.admin_user.id)
        self.assertEqual(data['user']['username'], self.admin_user.username)
        self.assertEqual(data['user']['role'], 'lab_admin')
    def test_user_permissions_lab_admin_access(self):
        """Test that lab_admin can access user permissions API"""
        self.client.login(username='lab_admin', password='testpass123')
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.lab_manager.id}))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['user']['role'], 'lab_manager')
    def test_user_permissions_nonexistent_user(self):
        """Test user permissions API with nonexistent user"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': 99999}))
        self.assertEqual(response.status_code, 404)  # Not found
    def test_user_permissions_role_permissions_data(self):
        """Test that role permissions data is correctly returned"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.admin_user.id}))
        data = json.loads(response.content)
        # Check that role permissions are returned
        role_permissions = data['role_permissions']
        self.assertIsInstance(role_permissions, list)
        # Lab admin should have admin permissions
        admin_permissions = [perm for perm in role_permissions if 'admin' in perm]
        self.assertGreater(len(admin_permissions), 0)


class GrantObjectPermissionAPITest(APITestCase):
    """Test cases for grant object permission API"""
    def test_grant_permission_requires_login(self):
        """Test that grant permission API requires authentication"""
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_grant_permission_requires_lab_manager_role(self):
        """Test that grant permission API requires lab_manager role or higher"""
        self.client.login(username='researcher', password='testpass123')
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 403)  # Forbidden
    def test_grant_permission_requires_post(self):
        """Test that grant permission API only accepts POST requests"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.get(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_grant_permission_missing_parameters(self):
        """Test grant permission API with missing parameters"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Missing required parameters')
    def test_grant_permission_invalid_model(self):
        """Test grant permission API with invalid model name"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:grant_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'InvalidModel',
            'object_id': self.sample.id,
            'permission_type': 'view'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid model name')
    def test_grant_permission_success(self):
        """Test successful grant permission API call"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:grant_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'sample',
            'object_id': self.sample.id,
            'permission_type': 'view'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('permission_id', data)
        self.assertEqual(data['message'], 'Permission granted successfully')
        # Check that permission was actually created
        permission = Permission.objects.get(id=data['permission_id'])
        self.assertEqual(permission.user, self.researcher)
        self.assertEqual(permission.permission_type, 'view')
        self.assertEqual(permission.object_id, self.sample.id)
    def test_grant_permission_with_expiration(self):
        """Test grant permission API with expiration date"""
        self.client.login(username='lab_manager', password='testpass123')
        expiration_date = (timezone.now() + timezone.timedelta(days=30)).isoformat()
        response = self.client.post(reverse('person:grant_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'sample',
            'object_id': self.sample.id,
            'permission_type': 'edit',
            'expires_at': expiration_date
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        # Check that permission was created with expiration
        permission = Permission.objects.get(id=data['permission_id'])
        self.assertIsNotNone(permission.expires_at)


class RevokeObjectPermissionAPITest(APITestCase):
    """Test cases for revoke object permission API"""
    def test_revoke_permission_requires_login(self):
        """Test that revoke permission API requires authentication"""
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_revoke_permission_requires_lab_manager_role(self):
        """Test that revoke permission API requires lab_manager role or higher"""
        self.client.login(username='researcher', password='testpass123')
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 403)  # Forbidden
    def test_revoke_permission_requires_post(self):
        """Test that revoke permission API only accepts POST requests"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.get(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    def test_revoke_permission_missing_parameters(self):
        """Test revoke permission API with missing parameters"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:revoke_object_permission_api'))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Missing required parameters')
    def test_revoke_permission_invalid_model(self):
        """Test revoke permission API with invalid model name"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:revoke_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'InvalidModel',
            'object_id': self.sample.id,
            'permission_type': 'view'
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid model name')
    def test_revoke_permission_nonexistent_permission(self):
        """Test revoke permission API for nonexistent permission"""
        self.client.login(username='lab_manager', password='testpass123')
        response = self.client.post(reverse('person:revoke_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'sample',
            'object_id': self.sample.id,
            'permission_type': 'view'
        })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Permission not found')
    def test_revoke_permission_success(self):
        """Test successful revoke permission API call"""
        self.client.login(username='lab_manager', password='testpass123')
        # First grant a permission
        content_type = ContentType.objects.get_for_model(Sample)
        permission = Permission.objects.create(
            user=self.researcher,
            content_type=content_type,
            object_id=self.sample.id,
            permission_type='view',
            granted_by=self.lab_manager
        )
        # Then revoke it
        response = self.client.post(reverse('person:revoke_object_permission_api'), {
            'user_id': self.researcher.id,
            'model_name': 'sample',
            'object_id': self.sample.id,
            'permission_type': 'view'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Permission revoked successfully')
        # Check that permission was actually deleted
        self.assertFalse(Permission.objects.filter(id=permission.id).exists())


class StorageCapacityAPITest(APITestCase):
    """Test cases for storage capacity API"""
    def test_storage_capacity_requires_login(self):
        """Test that storage capacity API requires authentication"""
        response = self.client.get(reverse('storage:capacity'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_storage_capacity_authenticated_user(self):
        """Test storage capacity API for authenticated user"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('storage:capacity'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('sites', data)
        self.assertIn('total_slots', data)
        self.assertIn('used_slots', data)
        self.assertIn('free_slots', data)
    def test_storage_capacity_data_accuracy(self):
        """Test that storage capacity returns accurate data"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('storage:capacity'))
        data = json.loads(response.content)
        # Check that capacity data is accurate
        total_slots = self.box.rows * self.box.columns
        self.assertEqual(data['total_slots'], total_slots)
        self.assertEqual(data['free_slots'], total_slots)  # No tubes stored yet
        self.assertEqual(data['used_slots'], 0)
        # Check site data
        self.assertIn(self.site.name, data['sites'])
        site_data = data['sites'][self.site.name]
        self.assertEqual(site_data['total_slots'], total_slots)
    def test_storage_capacity_with_stored_tubes(self):
        """Test storage capacity with stored tubes"""
        self.client.login(username='admin', password='testpass123')
        # Store some tubes
        self.aliquot.create_tubes(auto_store=True)
        response = self.client.get(reverse('storage:capacity'))
        data = json.loads(response.content)
        # Check that used slots reflect stored tubes
        self.assertEqual(data['used_slots'], 5)  # 5 tubes created
        self.assertEqual(data['free_slots'], (self.box.rows * self.box.columns) - 5)


class APIErrorHandlingTest(APITestCase):
    """Test cases for API error handling"""
    def test_api_404_handling(self):
        """Test API 404 error handling"""
        self.client.login(username='admin', password='testpass123')
        # Test with nonexistent user
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': 99999}))
        self.assertEqual(response.status_code, 404)
    def test_api_403_handling(self):
        """Test API 403 error handling"""
        self.client.login(username='researcher', password='testpass123')
        # Test accessing admin-only endpoint
        response = self.client.get(reverse('person:user_permissions_api', kwargs={'user_id': self.admin_user.id}))
        self.assertEqual(response.status_code, 403)
    def test_api_405_handling(self):
        """Test API 405 error handling"""
        self.client.login(username='admin', password='testpass123')
        # Test POST-only endpoint with GET
        response = self.client.get(reverse('toggle_theme'))
        self.assertEqual(response.status_code, 405)
    def test_api_400_handling(self):
        """Test API 400 error handling"""
        self.client.login(username='lab_manager', password='testpass123')
        # Test with missing parameters
        response = self.client.post(reverse('person:grant_object_permission_api'))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)


class APIPerformanceTest(APITestCase):
    """Test cases for API performance"""
    def test_dashboard_stats_performance(self):
        """Test dashboard stats API performance"""
        self.client.login(username='admin', password='testpass123')
        # Create additional test data
        for i in range(10):
            Sample.objects.create(
                name=f"Performance Test Sample {i}",
                source=self.source
            )
        # Test response time
        import time
        start_time = time.time()
        response = self.client.get(reverse('dashboard_stats'))
        end_time = time.time()
        self.assertEqual(response.status_code, 200)
        # Response should be under 1 second
        self.assertLess(end_time - start_time, 1.0)
    def test_storage_capacity_performance(self):
        """Test storage capacity API performance"""
        self.client.login(username='admin', password='testpass123')
        # Create additional storage devices
        for i in range(5):
            device = Device.objects.create(
                name=f"Performance Device {i}",
                site=self.site
            )
            shelf = Shelf.objects.create(
                name=f"Performance Shelf {i}",
                device=device
            )
            rack = Rack.objects.create(
                name=f"Performance Rack {i}",
                shelf=shelf
            )
            Box.objects.create(
                name=f"Performance Box {i}",
                rack=rack,
                rows=10,
                columns=10
            )
        # Test response time
        import time
        start_time = time.time()
        response = self.client.get(reverse('storage:capacity'))
        end_time = time.time()
        self.assertEqual(response.status_code, 200)
        # Response should be under 1 second
        self.assertLess(end_time - start_time, 1.0)
