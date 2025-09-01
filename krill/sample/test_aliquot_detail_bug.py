"""
Test for aliquot detail view bug
This test reproduces the error that occurs when accessing an aliquot detail page.
The error is: Unsupported lookup 'dispositionType' for ForeignKey or join on the field not permitted.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sample.models.sample import Sample
from sample.models.aliquot import Aliquot, AliquotType, AliquotDisposition, AliquotTube
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Device, Shelf, Rack, Box

User = get_user_model()


class AliquotDetailBugTest(TestCase):
    """Test cases for aliquot detail view bug"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test source and sample
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        
        # Create aliquot type
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="Test aliquot type"
        )
        
        # Create aliquot
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            quantity=3
        )
        
        # Create disposition
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        
        # Create tubes for the aliquot
        for i in range(1, 4):  # Create 3 tubes
            AliquotTube.objects.create(
                aliquot=self.aliquot,
                tube_number=i,
                disposition=self.stored_disposition
            )
        
        # Create storage hierarchy for testing storage locations
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
        """Test that aliquot detail view loads without the dispositionType lookup error"""
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})
        
        # This should not raise an error
        response = self.client.get(url)
        
        # Should return 200, not 500
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sample/detail.html')
        
        # Check that the aliquot object is in context
        self.assertIn('object', response.context)
        self.assertEqual(response.context['object'], self.aliquot)
        self.assertEqual(response.context['model_type'], 'aliquot')
        
        # Check that tubes are in context
        self.assertIn('tubes', response.context)
        tubes = response.context['tubes']
        self.assertEqual(tubes.count(), 3)  # Should have 3 tubes
        
        # Check that the aliquot has the correct disposition counts
        self.assertEqual(self.aliquot.stored_tubes_count, 3)  # All tubes are stored
        self.assertEqual(self.aliquot.in_use_tubes_count, 0)  # No tubes in use
        self.assertEqual(self.aliquot.exhausted_tubes_count, 0)  # No tubes exhausted
        
        # Check that storage locations are handled correctly
        self.assertIn('storage_locations', response.context)
        # Since tubes are stored but not in locations, this should be None
        self.assertIsNone(response.context['storage_locations'])
    
    def test_aliquot_detail_view_with_storage_locations(self):
        """Test aliquot detail view when tubes are actually stored in locations"""
        from sample.models.aliquot import AliquotLocation
        
        # Create storage locations for the tubes
        for i in range(1, 4):
            AliquotLocation.objects.create(
                aliquot=self.aliquot,
                tube_number=i,
                box=self.box,
                row=1,
                column=i
            )
        
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})
        
        # This should not raise an error
        response = self.client.get(url)
        
        # Should return 200, not 500
        self.assertEqual(response.status_code, 200)
        
        # Check that storage locations are in context
        self.assertIn('storage_locations', response.context)
        storage_locations = response.context['storage_locations']
        self.assertIsNotNone(storage_locations)
        self.assertEqual(len(storage_locations), 3)  # Should have 3 locations
        
        # Check location details
        for i, location in enumerate(storage_locations):
            self.assertEqual(location['tube_number'], i + 1)
            self.assertEqual(location['row'], 1)
            self.assertEqual(location['column'], i + 1)
            self.assertEqual(location['box'], self.box)
    
    def test_aliquot_detail_view_with_mixed_dispositions(self):
        """Test aliquot detail view with tubes having different dispositions"""
        # Create different dispositions
        in_use_disposition = AliquotDisposition.objects.create(
            name="In Use",
            disposition_type="in_use"
        )
        exhausted_disposition = AliquotDisposition.objects.create(
            name="Exhausted",
            disposition_type="exhausted"
        )
        
        # Update tube dispositions
        self.aliquot.tubes.filter(tube_number=1).update(disposition=self.stored_disposition)
        self.aliquot.tubes.filter(tube_number=2).update(disposition=in_use_disposition)
        self.aliquot.tubes.filter(tube_number=3).update(disposition=exhausted_disposition)
        
        # Refresh the aliquot from database to get updated tube dispositions
        self.aliquot.refresh_from_db()
        
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})
        
        # This should not raise an error
        response = self.client.get(url)
        
        # Should return 200, not 500
        self.assertEqual(response.status_code, 200)
        
        # Check that the aliquot has the correct disposition counts
        self.assertEqual(self.aliquot.stored_tubes_count, 1)  # 1 tube stored
        self.assertEqual(self.aliquot.in_use_tubes_count, 1)  # 1 tube in use
        self.assertEqual(self.aliquot.exhausted_tubes_count, 1)  # 1 tube exhausted
        
        # Check that only stored tubes are considered for storage locations
        self.assertIn('storage_locations', response.context)
        storage_locations = response.context['storage_locations']
        self.assertIsNone(storage_locations)  # Only 1 tube is stored, but no locations created
    
    def test_aliquot_detail_view_requires_login(self):
        """Test that aliquot detail view requires login"""
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_aliquot_detail_view_nonexistent_aliquot(self):
        """Test accessing detail view for non-existent aliquot"""
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
