"""
Test for storage detail view editing functionality
This test reproduces the error that occurs when editing a site name on the detail page.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from storage.models.site import Site
from storage.models.storage import Device, Shelf, Rack, Box

User = get_user_model()


class StorageDetailEditTest(TestCase):
    """Test cases for storage detail view editing functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test site
        self.site = Site.objects.create(
            name="Original Site Name",
            description="Original description"
        )

        # Create full storage hierarchy
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

        # Check that the site object is in context
        self.assertEqual(response.context['object'], self.site)
        self.assertEqual(response.context['model_type'], 'site')

        # Check that form is populated with site data
        form = response.context['form']
        self.assertEqual(form.instance, self.site)
        self.assertEqual(form.initial.get('name'), 'Original Site Name')
        self.assertEqual(form.initial.get('description'), 'Original description')

    def test_site_detail_view_post_edit_name(self):
        """Test editing a site name via POST request - this should reproduce the error"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})

        # Prepare form data with updated name
        form_data = {
            'name': 'Updated Site Name',
            'description': 'Updated description'
        }

        # Make POST request to edit the site
        response = self.client.post(url, data=form_data)

        # This test should fail initially, reproducing the error
        # Once fixed, it should redirect to storage list
        self.assertEqual(response.status_code, 302)  # Should redirect after successful edit

        # Check that the site was actually updated in the database
        updated_site = Site.objects.get(pk=self.site.pk)
        self.assertEqual(updated_site.name, 'Updated Site Name')
        self.assertEqual(updated_site.description, 'Updated description')

    def test_site_detail_view_post_invalid_data(self):
        """Test POST request with invalid data"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})

        # Prepare invalid form data (missing required name field)
        form_data = {
            'name': '',  # Empty name should be invalid
            'description': 'Updated description'
        }

        # Make POST request with invalid data
        response = self.client.post(url, data=form_data)

        # Should return 200 with form errors, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/detail.html')

        # Check that form has errors
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

        # Check that the site was NOT updated in the database
        unchanged_site = Site.objects.get(pk=self.site.pk)
        self.assertEqual(unchanged_site.name, 'Original Site Name')
        self.assertEqual(unchanged_site.description, 'Original description')

    def test_device_detail_view_post_edit(self):
        """Test editing a device via POST request"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'device', 'pk': self.device.pk})

        # Prepare form data with updated device info
        form_data = {
            'name': 'Updated Device Name',
            'description': 'Updated device description',
            'site': self.site.pk,
            'auto_store_enabled': True
        }

        # Make POST request to edit the device
        response = self.client.post(url, data=form_data)

        # Debug: Check if there are form errors
        if response.status_code == 200:
            self.assertIn('form', response.context)
            form = response.context['form']
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
                print(f"Form data: {form_data}")

        # Should redirect after successful edit
        self.assertEqual(response.status_code, 302)

        # Check that the device was actually updated in the database
        updated_device = Device.objects.get(pk=self.device.pk)
        self.assertEqual(updated_device.name, 'Updated Device Name')
        self.assertEqual(updated_device.description, 'Updated device description')
        self.assertTrue(updated_device.auto_store_enabled)

    def test_box_detail_view_post_edit(self):
        """Test editing a box via POST request"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'box', 'pk': self.box.pk})

        # Prepare form data with updated box info
        form_data = {
            'name': 'Updated Box Name',
            'description': 'Updated box description',
            'rack': self.rack.pk,
            'rows': 8,
            'columns': 12
        }

        # Make POST request to edit the box
        response = self.client.post(url, data=form_data)

        # Debug: Check if there are form errors
        if response.status_code == 200:
            self.assertIn('form', response.context)
            form = response.context['form']
            if not form.is_valid():
                print(f"Form errors: {form.errors}")
                print(f"Form data: {form_data}")

        # Should redirect after successful edit
        self.assertEqual(response.status_code, 302)

        # Check that the box was actually updated in the database
        updated_box = Box.objects.get(pk=self.box.pk)
        self.assertEqual(updated_box.name, 'Updated Box Name')
        self.assertEqual(updated_box.description, 'Updated box description')
        self.assertEqual(updated_box.rows, 8)
        self.assertEqual(updated_box.columns, 12)

    def test_storage_detail_view_requires_login(self):
        """Test that storage detail view requires login"""
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': self.site.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_storage_detail_view_nonexistent_object(self):
        """Test accessing detail view for non-existent object"""
        self.client.force_login(self.user)
        url = reverse('storage:detail', kwargs={'type': 'site', 'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_storage_detail_view_invalid_type(self):
        """Test accessing detail view with invalid type"""
        self.client.force_login(self.user)
        # This should default to site type since 'invalid' is not handled
        url = reverse('storage:detail', kwargs={'type': 'invalid', 'pk': self.site.pk})
        response = self.client.get(url)
        # Should still work because it defaults to site
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['model_type'], 'invalid')
