"""
Test for storage detail view editing functionality
This test reproduces the error that occurs when editing a site name on the detail page.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models.site import Site
from ..models.storage import Device, Shelf, Rack, Box

User = get_user_model()


class StorageDetailEditTest(TestCase):
    """Test cases for storage detail view editing functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.site = Site.objects.create(
            name="Original Site Name",
            description="Original description"
        )

        self.device = Device.objects.create(
            name="Test Device",
            site=self.site
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

    def test_site_detail_view_get(self):
        """Test that site detail view loads correctly"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/detail.html')
        self.assertIn('object', response.context)
        self.assertIn('form', response.context)
        self.assertIn('model_type', response.context)

        self.assertEqual(response.context['object'], self.site)
        self.assertEqual(response.context['model_type'], 'site')

        form = response.context['form']
        self.assertEqual(form.instance, self.site)
        self.assertEqual(form.initial.get('name'), 'Original Site Name')
        self.assertEqual(form.initial.get('description'), 'Original description')

    def test_site_detail_view_post_edit_name(self):
        """Test editing a site name via POST request"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})

        form_data = {
            'name': 'Updated Site Name',
            'description': 'Updated description'
        }

        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)

        updated_site = Site.objects.get(pk=self.site.pk)
        self.assertEqual(updated_site.name, 'Updated Site Name')
        self.assertEqual(updated_site.description, 'Updated description')

    def test_site_detail_view_post_invalid_data(self):
        """Test POST request with invalid data"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})

        form_data = {
            'name': '',
            'description': 'Updated description'
        }

        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/detail.html')

        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

        unchanged_site = Site.objects.get(pk=self.site.pk)
        self.assertEqual(unchanged_site.name, 'Original Site Name')
        self.assertEqual(unchanged_site.description, 'Original description')

    def test_device_detail_view_post_edit(self):
        """Test editing a device via POST request"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'device', 'pk': self.device.pk})

        form_data = {
            'name': 'Updated Device Name',
            'description': 'Updated device description',
            'site': self.site.pk,
            'auto_store_enabled': True
        }

        response = self.client.post(url, data=form_data)

        if response.status_code == 200:
            self.assertIn('form', response.context)
            form = response.context['form']
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
                print(f"Form data: {form_data}")

        self.assertEqual(response.status_code, 302)

        updated_device = Device.objects.get(pk=self.device.pk)
        self.assertEqual(updated_device.name, 'Updated Device Name')
        self.assertEqual(updated_device.description, 'Updated device description')
        self.assertTrue(updated_device.auto_store_enabled)

    def test_box_detail_view_post_edit(self):
        """Test editing a box via POST request"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'box', 'pk': self.box.pk})

        form_data = {
            'name': 'Updated Box Name',
            'description': 'Updated box description',
            'rack': self.rack.pk,
            'rows': 8,
            'columns': 12
        }

        response = self.client.post(url, data=form_data)

        if response.status_code == 200:
            self.assertIn('form', response.context)
            form = response.context['form']
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
                print(f"Form data: {form_data}")

        self.assertEqual(response.status_code, 302)

        updated_box = Box.objects.get(pk=self.box.pk)
        self.assertEqual(updated_box.name, 'Updated Box Name')
        self.assertEqual(updated_box.description, 'Updated box description')
        self.assertEqual(updated_box.rows, 8)
        self.assertEqual(updated_box.columns, 12)

    def test_storage_detail_view_requires_login(self):
        """Test that storage detail view requires login"""
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_storage_detail_view_nonexistent_object(self):
        """Test accessing detail view for non-existent object"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_storage_detail_view_invalid_type(self):
        """Test accessing detail view with invalid type"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'invalid', 'pk': self.site.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['model_type'], 'invalid')
