from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..models.storage import Device, Shelf, Rack, Box
from ..models.site import Site
from sample.models.sample import Sample
from sample.models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation, AliquotTube
)
from sample.models.source import Source
from person.models import UserRole, UserAuditLog

User = get_user_model()


class StorageViewTestBase(TestCase):
    """Base test class for storage views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user_role = self.user.role
        self.user_role.role = 'lab_member'
        self.user_role.save()
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site,
            auto_store_enabled=True
        )
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
            rows=10,
            columns=10
        )
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )


class StorageListViewTest(StorageViewTestBase):
    """Test cases for the StorageListView"""
    def test_storage_list_requires_login(self):
        """Test that storage list requires login"""
        response = self.client.get(reverse('storage:storage_list'))
        self.assertEqual(response.status_code, 302)
    def test_storage_list_get_request_default(self):
        """Test storage list GET request with default type (site)"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Sites')
        items = response.context['items']
        self.assertIn(self.site, items)
    def test_storage_list_get_request_box_type(self):
        """Test storage list GET request with box type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage_list'), {'type': 'box'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Boxes')
        items = response.context['items']
        self.assertIn(self.box, items)
    def test_storage_list_get_request_shelf_type(self):
        """Test storage list GET request with shelf type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage_list'), {'type': 'shelf'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Shelves')
        items = response.context['items']
        self.assertIn(self.shelf, items)
    def test_storage_list_get_request_device_type(self):
        """Test storage list GET request with device type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage_list'), {'type': 'device'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Devices')
        items = response.context['items']
        self.assertIn(self.device, items)


class HomeViewTest(StorageViewTestBase):
    """Test cases for the HomeView"""
    def test_home_view_requires_login(self):
        """Test that home view requires login"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
    def test_home_view_get_request(self):
        """Test home view GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'krill/home.html')
        self.assertIn('stats', response.context)
        self.assertIn('recent_activity', response.context)
        stats = response.context['stats']
        self.assertIn('active_samples', stats)
        self.assertIn('storage_usage', stats)
        self.assertIn('recent_reports', stats)
        self.assertIn('alerts', stats)
        self.assertIn('total_slots', stats)
        self.assertIn('used_slots', stats)
        recent_activity = response.context['recent_activity']
        self.assertIsInstance(recent_activity, list)

    def test_recent_activity_view_all_links_to_audit_log(self):
        """Regression: Recent Activity 'View All' must link to Audit Log, not Samples."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        audit_log_url = reverse('person:audit_log')
        self.assertIn(
            audit_log_url.encode(),
            response.content,
            msg="Recent Activity 'View All' should link to audit log",
        )
        self.assertIn(b'view-all', response.content)
        self.assertIn(b'recent-activity', response.content)

    def test_recent_activity_uses_correct_detail_url_patterns(self):
        """Regression: Recent Activity items must use detail/sample/<pk>/ and detail/aliquot/<pk>/."""
        self.client.force_login(self.user)
        UserAuditLog.log_action(
            user=self.user,
            action='sample_created',
            target_type='Sample',
            target_id=self.sample.id,
            target_name=self.sample.name,
        )
        UserAuditLog.log_action(
            user=self.user,
            action='aliquot_created',
            target_type='Aliquot',
            target_id=self.aliquot.id,
            target_name=str(self.aliquot),
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(
            '/samples/detail/sample/',
            content,
            msg="Recent Activity sample links must use detail/sample/<pk>/",
        )
        self.assertIn(
            '/samples/detail/aliquot/',
            content,
            msg="Recent Activity aliquot links must use detail/aliquot/<pk>/",
        )


class StorageMainViewTest(StorageViewTestBase):
    """Test cases for the StorageView"""
    def test_storage_view_requires_login(self):
        """Test that storage view requires login"""
        response = self.client.get(reverse('storage:storage'))
        self.assertEqual(response.status_code, 302)
    def test_storage_view_get_request(self):
        """Test storage view GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/storage.html')


class DashboardStatsViewTest(StorageViewTestBase):
    """Test cases for the dashboard_stats view"""
    def test_dashboard_stats_requires_login(self):
        """Test that dashboard stats requires login"""
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 302)
    def test_dashboard_stats_get_request(self):
        """Test dashboard stats GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('active_samples', data)
        self.assertIn('storage_usage', data)
        self.assertIn('recent_reports', data)
        self.assertIn('alerts', data)
        self.assertIn('total_slots', data)
        self.assertIn('used_slots', data)
        self.assertIsInstance(data['active_samples'], int)
        self.assertIsInstance(data['storage_usage'], int)
        self.assertIsInstance(data['recent_reports'], int)
        self.assertIsInstance(data['alerts'], int)
        self.assertIsInstance(data['total_slots'], int)
        self.assertIsInstance(data['used_slots'], int)
        self.assertGreaterEqual(data['active_samples'], 0)
        self.assertGreaterEqual(data['storage_usage'], 0)
        self.assertLessEqual(data['storage_usage'], 100)
        self.assertGreaterEqual(data['recent_reports'], 0)
        self.assertGreaterEqual(data['alerts'], 0)
        self.assertGreaterEqual(data['total_slots'], 0)
        self.assertGreaterEqual(data['used_slots'], 0)
    def test_dashboard_stats_with_sample_data(self):
        """Test dashboard stats with sample data"""
        self.client.force_login(self.user)
        sample2 = Sample.objects.create(name="Test Sample 2", source=self.source)
        sample3 = Sample.objects.create(name="Test Sample 3", source=self.source)
        location1 = AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
            tube_number=1
        )
        location2 = AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=2,
            tube_number=2
        )
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active_samples'], 3)
        self.assertEqual(data['used_slots'], 2)
        self.assertEqual(data['total_slots'], 100)
        self.assertEqual(data['storage_usage'], 2)
