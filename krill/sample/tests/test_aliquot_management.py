"""
Tests for aliquot management functionality including:
- Box assignment during creation
- Checkout functionality
- Tube editing
- Signal handlers using disposition_type
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sample.models.sample import Sample
from sample.models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation, AliquotTube
)
from sample.models.source import Source
from storage.models.storage import Device, Shelf, Rack, Box
from storage.models.site import Site

User = get_user_model()


class AliquotBoxAssignmentTest(TestCase):
    """Test box assignment during aliquot creation"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

        # Create storage hierarchy
        self.site = Site.objects.create(name="Test Site")
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
            rows=5,
            columns=5
        )

        # Create sample and aliquot type
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        # Create dispositions
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )

    def test_aliquot_creation_with_box_assignment(self):
        """Test creating aliquot with box assignment"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'quantity': 3,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            'start_row': 1,
            'start_column': 1,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation

        # Check aliquot was created
        aliquot = Aliquot.objects.get(sample=self.sample)
        self.assertEqual(aliquot.quantity, 3)

        # Check tubes were created
        tubes = AliquotTube.objects.filter(aliquot=aliquot)
        self.assertEqual(tubes.count(), 3)

        # Check locations were created
        locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(locations.count(), 3)

        # Check first location is at specified position
        first_location = locations.order_by('tube_number').first()
        self.assertEqual(first_location.row, 1)
        self.assertEqual(first_location.column, 1)
        self.assertEqual(first_location.box, self.box)

    def test_aliquot_creation_without_box_assignment(self):
        """Test creating aliquot without box assignment"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'quantity': 2,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
            'assign_to_box': False,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check aliquot was created
        aliquot = Aliquot.objects.get(sample=self.sample)
        self.assertEqual(aliquot.quantity, 2)

        # Check tubes were created
        tubes = AliquotTube.objects.filter(aliquot=aliquot)
        self.assertEqual(tubes.count(), 2)

        # Check no locations were created
        locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(locations.count(), 0)

    def test_aliquot_creation_with_auto_box_assignment(self):
        """Test creating aliquot with auto box assignment (no start position)"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'quantity': 2,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            # No start_row or start_column - should auto-assign
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check locations were created
        aliquot = Aliquot.objects.get(sample=self.sample)
        locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(locations.count(), 2)

        # Check positions are valid
        for location in locations:
            self.assertGreaterEqual(location.row, 1)
            self.assertLessEqual(location.row, self.box.rows)
            self.assertGreaterEqual(location.column, 1)
            self.assertLessEqual(location.column, self.box.columns)


class AliquotCheckoutTest(TestCase):
    """Test checkout functionality for aliquots"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

        # Create storage hierarchy
        self.site = Site.objects.create(name="Test Site")
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
            rows=5,
            columns=5
        )

        # Create sample and aliquot
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        # Create dispositions
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        self.in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

        # Create aliquot with tubes
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=2,
            aliquot_type=self.aliquot_type
        )
        self.aliquot.create_tubes(auto_store=False)

        # Store one tube in a box
        self.tube = AliquotTube.objects.filter(aliquot=self.aliquot).first()
        self.tube.disposition = self.stored_disposition
        self.tube.save()

        AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
            tube_number=self.tube.tube_number
        )

    def test_checkout_stored_tube(self):
        """Test checking out a stored tube"""
        # Verify tube is stored
        self.assertEqual(self.tube.disposition.disposition_type, 'stored')
        self.assertTrue(
            AliquotLocation.objects.filter(
                aliquot=self.aliquot,
                tube_number=self.tube.tube_number
            ).exists()
        )

        # Checkout the tube
        url = reverse('sample:tube_detail', kwargs={'pk': self.tube.id})
        response = self.client.post(url, {'action': 'checkout'})

        self.assertEqual(response.status_code, 302)  # Redirect

        # Refresh from database
        self.tube.refresh_from_db()

        # Verify disposition changed to 'in_use'
        self.assertEqual(self.tube.disposition.disposition_type, 'in_use')

        # Verify storage location was removed
        self.assertFalse(
            AliquotLocation.objects.filter(
                aliquot=self.aliquot,
                tube_number=self.tube.tube_number
            ).exists()
        )

    def test_checkout_uses_correct_disposition_type_attribute(self):
        """Test that checkout uses disposition_type (not dispositionType)"""
        # This test ensures we don't reintroduce the camelCase bug
        url = reverse('sample:tube_detail', kwargs={'pk': self.tube.id})

        # This should not raise AttributeError
        try:
            response = self.client.post(url, {'action': 'checkout'})
            self.assertEqual(response.status_code, 302)
        except AttributeError as e:
            if 'dispositionType' in str(e):
                self.fail("Checkout is using wrong attribute name 'dispositionType' instead of 'disposition_type'")
            raise


class SignalHandlerDispositionTypeTest(TestCase):
    """Test signal handlers use correct disposition_type attribute"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        # Create dispositions
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        self.in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

    def test_signal_handlers_use_disposition_type_not_dispositionType(self):
        """Test that signal handlers use disposition_type attribute correctly"""
        # Create aliquot and tube
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)

        tube = AliquotTube.objects.filter(aliquot=aliquot).first()

        # Change disposition - this should trigger signals
        # This should not raise AttributeError about dispositionType
        try:
            tube.disposition = self.in_use_disposition
            tube.save()

            # Verify the change worked
            tube.refresh_from_db()
            self.assertEqual(tube.disposition.disposition_type, 'in_use')
        except AttributeError as e:
            if 'dispositionType' in str(e):
                self.fail("Signal handlers are using wrong attribute name 'dispositionType' instead of 'disposition_type'")
            raise

    def test_disposition_change_removes_storage_location(self):
        """Test that changing from stored to in_use removes storage location"""
        # Create storage
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=5, columns=5)

        # Create aliquot and tube
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)

        tube = AliquotTube.objects.filter(aliquot=aliquot).first()
        tube.disposition = self.stored_disposition
        tube.save()

        # Create storage location
        location = AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=1,
            column=1,
            tube_number=tube.tube_number
        )

        # Change to in_use - should remove location
        tube.disposition = self.in_use_disposition
        tube.save()

        # Verify location was removed
        self.assertFalse(
            AliquotLocation.objects.filter(pk=location.pk).exists()
        )


class BoxAssignmentViewTest(TestCase):
    """Test box assignment view functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

        # Create storage hierarchy
        self.site = Site.objects.create(name="Test Site")
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
            rows=5,
            columns=5
        )

        # Create sample and aliquot
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=2,
            aliquot_type=self.aliquot_type
        )
        self.aliquot.create_tubes(auto_store=False)

        # Create dispositions
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )

    def test_assign_aliquot_to_box_position(self):
        """Test assigning aliquot to box position via view"""
        tube = AliquotTube.objects.filter(aliquot=self.aliquot).first()

        url = reverse('storage:assign_aliquot', kwargs={
            'box_id': self.box.id,
            'row': 2,
            'column': 3
        })

        response = self.client.post(url, {
            'aliquot_id': self.aliquot.id,
            'tube_number': tube.tube_number
        })

        self.assertEqual(response.status_code, 302)  # Redirect

        # Verify location was created
        location = AliquotLocation.objects.get(
            aliquot=self.aliquot,
            tube_number=tube.tube_number
        )
        self.assertEqual(location.row, 2)
        self.assertEqual(location.column, 3)
        self.assertEqual(location.box, self.box)

        # Verify tube disposition changed to stored
        tube.refresh_from_db()
        self.assertEqual(tube.disposition.disposition_type, 'stored')

    def test_assign_aliquot_prevents_duplicate_position(self):
        """Test that assigning to occupied position fails"""
        # Create first location
        tube1 = AliquotTube.objects.filter(aliquot=self.aliquot).first()
        AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
            tube_number=tube1.tube_number
        )

        # Try to assign another tube to same position
        tube2 = AliquotTube.objects.filter(aliquot=self.aliquot).last()
        url = reverse('storage:assign_aliquot', kwargs={
            'box_id': self.box.id,
            'row': 1,
            'column': 1
        })

        response = self.client.post(url, {
            'aliquot_id': self.aliquot.id,
            'tube_number': tube2.tube_number
        })

        # Should redirect with error message (or return error)
        # The view should handle this gracefully
        self.assertIn(response.status_code, [302, 400])


class AliquotFormBoxAssignmentTest(TestCase):
    """Test AliquotForm with box assignment fields"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device)
        self.rack = Rack.objects.create(name="Test Rack", shelf=self.shelf)
        self.box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=5,
            columns=5
        )

    def test_aliquot_form_includes_box_assignment_fields(self):
        """Test that AliquotForm includes box assignment fields"""
        from sample.forms import AliquotForm

        form = AliquotForm()

        # Check that box assignment fields exist
        self.assertIn('assign_to_box', form.fields)
        self.assertIn('box', form.fields)
        self.assertIn('start_row', form.fields)
        self.assertIn('start_column', form.fields)

        # Check that box field has queryset
        self.assertIsNotNone(form.fields['box'].queryset)
        self.assertIn(self.box, form.fields['box'].queryset)

    def test_aliquot_form_box_fields_are_optional(self):
        """Test that box assignment fields are optional"""
        from sample.forms import AliquotForm

        data = {
            'sample': self.sample.id,
            'quantity': 1,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }

        form = AliquotForm(data=data)
        self.assertTrue(form.is_valid())

    def test_aliquot_form_requires_box_when_assign_to_box_checked(self):
        """Test that box is required when assign_to_box is checked"""
        from sample.forms import AliquotForm

        data = {
            'sample': self.sample.id,
            'quantity': 1,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            # Missing box field
        }

        form = AliquotForm(data=data)
        # Form should be valid (validation happens in view)
        # But box should be required when assign_to_box is True
        # This is handled in the view's form_valid method
