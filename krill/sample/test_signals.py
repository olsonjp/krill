from django.test import TestCase

from .models.sample import Sample
from .models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation,
)
from .models.source import Source
from storage.models.storage import Device, Shelf, Rack, Box
from storage.models.site import Site


class SignalHandlerTest(TestCase):
    """Test cases for signal handlers"""
    def setUp(self):
        """Set up test data"""
        # Create storage hierarchy
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
        # Create sample data
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name="Stored",
            defaults={'disposition_type': 'stored'}
        )
        self.in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name="In Use",
            defaults={'disposition_type': 'in_use'}
        )
        self.exhausted_disposition, _ = AliquotDisposition.objects.get_or_create(
            name="Exhausted",
            defaults={'disposition_type': 'exhausted'}
        )


class AliquotCreationTest(SignalHandlerTest):
    """Test aliquot creation"""

    def test_aliquot_creation_with_disposition(self):
        """Test that aliquot is created with a disposition"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.assertEqual(aliquot.disposition, self.stored_disposition)

    def test_multiple_aliquots_independent(self):
        """Test creating multiple independent aliquots"""
        aliquots = []
        for i in range(5):
            a = Aliquot.objects.create(
                sample=self.sample,
                aliquot_type=self.aliquot_type,
                disposition=self.stored_disposition,
            )
            aliquots.append(a)
        self.assertEqual(len(aliquots), 5)
        self.assertEqual(Aliquot.objects.filter(sample=self.sample).count(), 5)


class AutoStorageTest(SignalHandlerTest):
    """Test auto-storage functionality"""

    def test_auto_store_function(self):
        """Test the auto_store_aliquot_tubes function"""
        from .signals import auto_store_aliquot_tubes

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        auto_store_aliquot_tubes(aliquot)

        location = AliquotLocation.objects.get(aliquot=aliquot)
        self.assertEqual(location.box, self.box)
        self.assertIn(location.row, range(1, 11))
        self.assertIn(location.column, range(1, 11))

    def test_auto_store_disabled_device(self):
        """Test that auto-store does not store in disabled devices"""
        from .signals import auto_store_aliquot_tubes

        self.device.auto_store_enabled = False
        self.device.save()

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        auto_store_aliquot_tubes(aliquot)

        # No location should be created (no auto-store enabled boxes)
        self.assertFalse(AliquotLocation.objects.filter(aliquot=aliquot).exists())

    def test_auto_store_box_selection(self):
        """Test auto-store box selection algorithm"""
        from .signals import auto_store_aliquot_tubes

        # Disable the default device
        self.device.auto_store_enabled = False
        self.device.save()

        # Create a new auto-store enabled device
        auto_store_device = Device.objects.create(
            name="Auto-Store Device",
            site=self.site,
            auto_store_enabled=True
        )
        auto_store_shelf = Shelf.objects.create(name="Auto-Store Shelf", device=auto_store_device)
        auto_store_rack = Rack.objects.create(name="Auto-Store Rack", shelf=auto_store_shelf)
        auto_store_box = Box.objects.create(
            name="Auto-Store Box", rack=auto_store_rack, rows=5, columns=5
        )

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        auto_store_aliquot_tubes(aliquot)

        location = AliquotLocation.objects.get(aliquot=aliquot)
        self.assertEqual(location.box, auto_store_box)

    def test_auto_store_inheritance_from_device_to_box(self):
        """Test auto-store inheritance from device to box"""
        self.assertTrue(self.box.auto_store_enabled)
        self.device.auto_store_enabled = False
        self.device.save()
        self.assertFalse(self.box.auto_store_enabled)


class AliquotDispositionTest(SignalHandlerTest):
    """Test aliquot disposition management"""

    def test_disposition_change(self):
        """Test changing disposition directly"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        aliquot.disposition = self.in_use_disposition
        aliquot.save()
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition.disposition_type, 'in_use')

    def test_multiple_aliquots_independent_dispositions(self):
        """Test that multiple aliquots have independent dispositions"""
        a1 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        a2 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        a3 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        # Change some dispositions
        a1.disposition = self.in_use_disposition
        a1.save()
        a2.disposition = self.exhausted_disposition
        a2.save()

        a1.refresh_from_db()
        a2.refresh_from_db()
        a3.refresh_from_db()

        self.assertEqual(a1.disposition.disposition_type, 'in_use')
        self.assertEqual(a2.disposition.disposition_type, 'exhausted')
        self.assertEqual(a3.disposition.disposition_type, 'stored')
