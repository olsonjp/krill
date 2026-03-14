"""
Test for aliquot detail view.
Ensures that the aliquot detail page loads correctly with the new simplified model.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sample.models.sample import Sample
from sample.models.aliquot import Aliquot, AliquotType, AliquotDisposition, AliquotLocation
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Device, Shelf, Rack, Box

User = get_user_model()


class AliquotDetailBugTest(TestCase):
    """Test cases for aliquot detail view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )

        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="Test aliquot type"
        )

        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name="Stored",
            defaults={"disposition_type": "stored"},
        )

        # Create one aliquot (each physical item = one aliquot)
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device)
        self.rack = Rack.objects.create(name="Test Rack", shelf=self.shelf)
        self.box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=10,
            columns=10
        )

    def test_aliquot_detail_view_loads_without_error(self):
        """Test that aliquot detail view loads without error"""
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/detail.html')
        self.assertIn('object', response.context)
        self.assertEqual(response.context['object'], self.aliquot)
        self.assertEqual(response.context['model_type'], 'aliquot')

    def test_aliquot_detail_view_disposition_directly_on_model(self):
        """Test that disposition is directly on the aliquot model"""
        self.assertEqual(self.aliquot.disposition, self.stored_disposition)
        self.assertEqual(self.aliquot.disposition.disposition_type, 'stored')

    def test_aliquot_detail_view_with_storage_location(self):
        """Test aliquot detail view when aliquot has a storage location"""
        AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1
        )

        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('storage_location', response.context)
        storage_location = response.context['storage_location']
        self.assertIsNotNone(storage_location)
        self.assertEqual(storage_location['row'], 1)
        self.assertEqual(storage_location['column'], 1)
        self.assertEqual(storage_location['box'], self.box)

    def test_aliquot_detail_view_without_storage_location(self):
        """Test aliquot detail view when aliquot has no storage location"""
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('storage_location', response.context)
        self.assertIsNone(response.context['storage_location'])

    def test_aliquot_detail_view_requires_login(self):
        """Test that aliquot detail view requires login"""
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_aliquot_detail_view_nonexistent_aliquot(self):
        """Test accessing detail view for non-existent aliquot"""
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
