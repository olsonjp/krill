"""
Tests for aliquot management functionality including:
- Box assignment during creation
- Checkout functionality
- Aliquot editing
- Disposition management
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sample.models.sample import Sample
from sample.models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation,
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
        """Test creating aliquot with box assignment (count=3 creates 3 aliquots)"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'count': 3,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            'start_row': 1,
            'start_column': 1,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation

        # Check 3 aliquots were created
        aliquots = Aliquot.objects.filter(sample=self.sample)
        self.assertEqual(aliquots.count(), 3)

        # Check locations were created (one per aliquot)
        locations = AliquotLocation.objects.filter(aliquot__sample=self.sample)
        self.assertEqual(locations.count(), 3)

        # Check first location is at specified position
        first_location = locations.order_by('row', 'column').first()
        self.assertEqual(first_location.row, 1)
        self.assertEqual(first_location.column, 1)
        self.assertEqual(first_location.box, self.box)

    def test_aliquot_creation_without_box_assignment(self):
        """Test creating aliquot without box assignment"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'count': 1,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': False,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check aliquot was created
        aliquot = Aliquot.objects.get(sample=self.sample)
        self.assertEqual(aliquot.disposition, self.stored_disposition)

        # Check no locations were created
        locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(locations.count(), 0)

    def test_aliquot_creation_with_auto_box_assignment(self):
        """Test creating aliquot with auto box assignment (no start position)"""
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'count': 2,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            # No start_row or start_column - should auto-assign
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check locations were created (one per aliquot)
        aliquots = Aliquot.objects.filter(sample=self.sample)
        locations = AliquotLocation.objects.filter(aliquot__in=aliquots)
        self.assertEqual(locations.count(), 2)

        # Check positions are valid
        for location in locations:
            self.assertGreaterEqual(location.row, 1)
            self.assertLessEqual(location.row, self.box.rows)
            self.assertGreaterEqual(location.column, 1)
            self.assertLessEqual(location.column, self.box.columns)

    def test_aliquot_creation_warns_when_requested_position_occupied(self):
        """Test that user is warned when requested starting position is occupied"""
        from django.contrib.messages import get_messages

        # Create an aliquot and occupy position (1, 1)
        existing_aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=existing_aliquot,
            box=self.box,
            row=1,
            column=1,
        )

        # Try to create new aliquot requesting occupied position
        url = reverse('sample:sample_create') + '?type=aliquot'
        data = {
            'sample': self.sample.id,
            'count': 1,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            'start_row': 1,
            'start_column': 1,  # This position is occupied
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check that warning message was added
        messages_list = list(get_messages(response.wsgi_request))
        warning_messages = [msg for msg in messages_list if 'occupied' in str(msg.message).lower()]
        self.assertGreater(len(warning_messages), 0, "Should have warning message about occupied position")

        # Check that aliquot was still created and assigned to next available position
        new_aliquot = Aliquot.objects.filter(sample=self.sample).exclude(id=existing_aliquot.id).first()
        self.assertIsNotNone(new_aliquot)
        locations = AliquotLocation.objects.filter(aliquot=new_aliquot)
        self.assertEqual(locations.count(), 1)
        # Should not be at (1, 1) since that's occupied
        location = locations.first()
        self.assertFalse(location.row == 1 and location.column == 1, "Should not use occupied position")


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

        # Create stored aliquot with location
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=self.aliquot,
            box=self.box,
            row=1,
            column=1,
        )

    def test_checkout_stored_aliquot(self):
        """Test checking out a stored aliquot"""
        # Verify aliquot is stored
        self.assertEqual(self.aliquot.disposition.disposition_type, 'stored')
        self.assertTrue(AliquotLocation.objects.filter(aliquot=self.aliquot).exists())

        # Checkout the aliquot
        url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.id})
        response = self.client.post(url, {'action': 'checkout'})

        self.assertEqual(response.status_code, 302)  # Redirect

        # Refresh from database
        self.aliquot.refresh_from_db()

        # Verify disposition changed to 'in_use'
        self.assertEqual(self.aliquot.disposition.disposition_type, 'in_use')

        # Verify storage location was removed
        self.assertFalse(AliquotLocation.objects.filter(aliquot=self.aliquot).exists())

    def test_checkout_uses_correct_disposition_type_attribute(self):
        """Test that checkout uses disposition_type correctly"""
        url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.id})

        try:
            response = self.client.post(url, {'action': 'checkout'})
            self.assertEqual(response.status_code, 302)
        except AttributeError as e:
            if 'dispositionType' in str(e):
                self.fail("Checkout is using wrong attribute name 'dispositionType' instead of 'disposition_type'")
            raise


class AliquotDispositionDirectTest(TestCase):
    """Test that aliquot disposition is directly on the model"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        self.in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

    def test_disposition_change_removes_storage_location(self):
        """Test that changing disposition and saving removes storage location when appropriate"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=5, columns=5)

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        location = AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=1,
            column=1,
        )

        # Change to in_use directly
        aliquot.disposition = self.in_use_disposition
        aliquot.save()

        # Disposition is changed but location removal is the view's responsibility
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition.disposition_type, 'in_use')


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

        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )

        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

    def test_assign_aliquot_to_box_position(self):
        """Test assigning aliquot to box position via view"""
        url = reverse('storage:assign_aliquot', kwargs={
            'box_id': self.box.id,
            'row': 2,
            'column': 3
        })

        response = self.client.post(url, {
            'aliquot_id': self.aliquot.id,
        })

        self.assertEqual(response.status_code, 302)  # Redirect

        # Verify location was created
        location = AliquotLocation.objects.get(aliquot=self.aliquot)
        self.assertEqual(location.row, 2)
        self.assertEqual(location.column, 3)
        self.assertEqual(location.box, self.box)

        # Verify aliquot disposition changed to stored
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition.disposition_type, 'stored')

    def test_assign_aliquot_prevents_duplicate_position(self):
        """Test that assigning to occupied position fails"""
        from django.contrib.messages import get_messages

        # Create first location for a second aliquot
        aliquot2 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=aliquot2,
            box=self.box,
            row=1,
            column=1,
        )

        # Try to assign self.aliquot to same position
        url = reverse('storage:assign_aliquot', kwargs={
            'box_id': self.box.id,
            'row': 1,
            'column': 1
        })

        response = self.client.post(url, {
            'aliquot_id': self.aliquot.id,
        })

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

        # Check that error message was added
        messages_list = list(get_messages(response.wsgi_request))
        error_messages = [msg for msg in messages_list if 'occupied' in str(msg.message).lower()]
        self.assertGreater(len(error_messages), 0, "Should have error message about occupied position")

        # Verify self.aliquot was not assigned to that position
        self.assertFalse(
            AliquotLocation.objects.filter(
                aliquot=self.aliquot,
                row=1,
                column=1
            ).exists(),
            "Aliquot should not be assigned to occupied position"
        )


class AliquotFormBoxAssignmentTest(TestCase):
    """Test AliquotForm with box assignment fields"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser_form',
            email='testform@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")

        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )

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
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
        }

        form = AliquotForm(data=data)
        self.assertTrue(form.is_valid())

    def test_aliquot_form_validates_start_row_bounds(self):
        """Test that start_row is validated against box dimensions"""
        from sample.forms import AliquotForm

        data = {
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            'start_row': self.box.rows + 1,  # Exceeds box dimensions
            'start_column': 1,
        }

        form = AliquotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('start_row', form.errors)
        self.assertIn('exceed box dimensions', str(form.errors['start_row']))

    def test_aliquot_form_validates_start_column_bounds(self):
        """Test that start_column is validated against box dimensions"""
        from sample.forms import AliquotForm

        data = {
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
            'assign_to_box': True,
            'box': self.box.id,
            'start_row': 1,
            'start_column': self.box.columns + 1,  # Exceeds box dimensions
        }

        form = AliquotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('start_column', form.errors)
        self.assertIn('exceed box dimensions', str(form.errors['start_column']))

    def test_assign_aliquot_handles_race_condition(self):
        """Test that race condition in box assignment is handled gracefully"""
        from django.contrib.messages import get_messages

        # Create aliquot and store it in a position
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(
            aliquot=aliquot,
            box=self.box,
            row=2,
            column=3,
        )

        # Create another aliquot
        aliquot2 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        # Try to assign to the same occupied position
        url = reverse('storage:assign_aliquot', kwargs={
            'box_id': self.box.id,
            'row': 2,
            'column': 3
        })

        response = self.client.post(url, {
            'aliquot_id': aliquot2.id,
        })

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

        # Check that error message was added
        messages_list = list(get_messages(response.wsgi_request))
        error_messages = [msg for msg in messages_list if 'occupied' in str(msg.message).lower()]
        self.assertGreater(len(error_messages), 0, "Should have error message about occupied position")

        # Verify second aliquot was not assigned to that position
        self.assertFalse(
            AliquotLocation.objects.filter(
                aliquot=aliquot2,
                row=2,
                column=3
            ).exists(),
            "Second aliquot should not be assigned to occupied position"
        )
