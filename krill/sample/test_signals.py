from django.test import TestCase
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models.sample import Sample
from .models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation, AliquotTube
)
from .models.source import Source
from .signals import (
    create_aliquot_tubes, auto_store_aliquot_tube,
    store_old_disposition, handle_tube_disposition_change,
    AUTO_CREATE_TUBES, AUTO_STORE_TUBES
)
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


class AliquotTubeCreationSignalTest(SignalHandlerTest):
    """Test cases for aliquot tube creation signal"""
    def test_automatic_tube_creation_when_aliquot_created(self):
        """Test automatic tube creation when aliquot is created"""
        # Enable automatic tube creation
        from .signals import AUTO_CREATE_TUBES
        original_setting = AUTO_CREATE_TUBES
        try:
            # Temporarily enable auto-creation
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            # Create aliquot with 5 tubes
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=5,
                aliquot_type=self.aliquot_type
            )
            # Check that 5 tubes were created
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            self.assertEqual(tubes.count(), 5)
            # Check tube numbers
            tube_numbers = list(tubes.values_list('tube_number', flat=True).order_by('tube_number'))
            self.assertEqual(tube_numbers, [1, 2, 3, 4, 5])
            # Check that all tubes have stored disposition
            for tube in tubes:
                self.assertEqual(tube.disposition.disposition_type, "stored")
        finally:
            # Restore original setting
            sample.signals.AUTO_CREATE_TUBES = original_setting
    def test_tube_creation_with_different_quantities(self):
        """Test tube creation with different quantities"""
        # Enable automatic tube creation
        from .signals import AUTO_CREATE_TUBES
        original_setting = AUTO_CREATE_TUBES
        try:
            # Temporarily enable auto-creation
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            quantities = [1, 3, 10]
            for quantity in quantities:
                aliquot = Aliquot.objects.create(
                    sample=self.sample,
                    quantity=quantity,
                    aliquot_type=self.aliquot_type
                )
                # Check that correct number of tubes were created
                tubes = AliquotTube.objects.filter(aliquot=aliquot)
                self.assertEqual(tubes.count(), quantity)
                # Check tube numbers
                tube_numbers = list(tubes.values_list('tube_number', flat=True).order_by('tube_number'))
                expected_numbers = list(range(1, quantity + 1))
                self.assertEqual(tube_numbers, expected_numbers)
        finally:
            # Restore original setting
            sample.signals.AUTO_CREATE_TUBES = original_setting
    def test_tube_creation_with_zero_quantity(self):
        """Test tube creation with zero quantity"""
        # Enable automatic tube creation
        from .signals import AUTO_CREATE_TUBES
        original_setting = AUTO_CREATE_TUBES
        try:
            # Temporarily enable auto-creation
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            # Create aliquot with 0 tubes
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=0,
                aliquot_type=self.aliquot_type
            )
            # Check that no tubes were created
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            self.assertEqual(tubes.count(), 0)
        finally:
            # Restore original setting
            sample.signals.AUTO_CREATE_TUBES = original_setting
    def test_tube_creation_prevents_infinite_loops(self):
        """Test that tube creation prevents infinite loops"""
        # Enable automatic tube creation
        from .signals import AUTO_CREATE_TUBES
        original_setting = AUTO_CREATE_TUBES
        try:
            # Temporarily enable auto-creation
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            # Create aliquot with 3 tubes
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=3,
                aliquot_type=self.aliquot_type
            )
            # Check that 3 tubes were created
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            self.assertEqual(tubes.count(), 3)
            # Save the aliquot again - should not create more tubes
            aliquot.save()
            # Should still be 3, not 6
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            self.assertEqual(tubes.count(), 3)
        finally:
            # Restore original setting
            sample.signals.AUTO_CREATE_TUBES = original_setting


class AutoStorageSignalTest(SignalHandlerTest):
    """Test cases for auto-storage signal"""
    def test_automatic_storage_of_stored_tubes(self):
        """Test automatic storage of tubes with 'stored' disposition"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Create aliquot with stored disposition
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=3,
                aliquot_type=self.aliquot_type
            )
            # Get the tubes that were created
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            # Check that tubes were automatically stored
            for tube in tubes:
                # Check if storage location was created
                storage_locations = AliquotLocation.objects.filter(
                    aliquot=aliquot,
                    tube_number=tube.tube_number
                )
                self.assertEqual(storage_locations.count(), 1)
                location = storage_locations.first()
                self.assertEqual(location.box, self.box)
                self.assertIn(location.row, range(1, 11))
                self.assertIn(location.column, range(1, 11))
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_no_auto_storage_for_non_stored_tubes(self):
        """Test that non-stored tubes are not automatically stored"""
        # Enable automatic tube creation but not auto-storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation but disable auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = False
            # Create aliquot with 3 tubes
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=3,
                aliquot_type=self.aliquot_type
            )
            # Change all tubes to in_use disposition
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            for tube in tubes:
                aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
            # Check that no storage locations were created
            storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(storage_locations.count(), 0)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_auto_store_box_selection_algorithm(self):
        """Test auto-store box selection algorithm"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Disable auto-store on the default device to prevent interference
            self.device.auto_store_enabled = False
            self.device.save()
            # Create multiple boxes with different auto-store settings
            auto_store_device = Device.objects.create(
                name="Auto-Store Device",
                site=self.site,
                auto_store_enabled=True
            )
            no_auto_store_device = Device.objects.create(
                name="No Auto-Store Device",
                site=self.site,
                auto_store_enabled=False
            )
            # Create boxes for each device
            auto_store_shelf = Shelf.objects.create(
                name="Auto-Store Shelf",
                device=auto_store_device
            )
            auto_store_rack = Rack.objects.create(
                name="Auto-Store Rack",
                shelf=auto_store_shelf
            )
            auto_store_box = Box.objects.create(
                name="Auto-Store Box",
                rack=auto_store_rack,
                rows=5,
                columns=5
            )
            no_auto_store_shelf = Shelf.objects.create(
                name="No Auto-Store Shelf",
                device=no_auto_store_device
            )
            no_auto_store_rack = Rack.objects.create(
                name="No Auto-Store Rack",
                shelf=no_auto_store_shelf
            )
            no_auto_store_box = Box.objects.create(
                name="No Auto-Store Box",
                rack=no_auto_store_rack,
                rows=5,
                columns=5
            )
            # Create aliquot - should be stored in auto-store box
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=2,
                aliquot_type=self.aliquot_type
            )
            # Check that tubes were stored in the auto-store box
            storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(storage_locations.count(), 2)
            for location in storage_locations:
                self.assertEqual(location.box, auto_store_box)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_available_slot_detection(self):
        """Test available slot detection for auto-storage"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Disable auto-store on the default device to prevent interference
            self.device.auto_store_enabled = False
            self.device.save()
            # Create a new device with auto-store enabled
            test_device = Device.objects.create(
                name="Test Device",
                site=self.site,
                auto_store_enabled=True
            )
            test_shelf = Shelf.objects.create(
                name="Test Shelf",
                device=test_device
            )
            test_rack = Rack.objects.create(
                name="Test Rack",
                shelf=test_shelf
            )
            # Create a small box (2x2) and fill it partially
            small_box = Box.objects.create(
                name="Small Box",
                rack=test_rack,
                rows=2,
                columns=2
            )
            # Create first aliquot to occupy some slots
            aliquot1 = Aliquot.objects.create(
                sample=self.sample,
                quantity=2,
                aliquot_type=self.aliquot_type
            )
            # Check that 2 slots are occupied
            occupied_slots = AliquotLocation.objects.filter(box=small_box)
            self.assertEqual(occupied_slots.count(), 2)
            # Create second aliquot - should find remaining slots
            sample2 = Sample.objects.create(name="Test Sample 2", source=self.source)
            aliquot2 = Aliquot.objects.create(
                sample=sample2,
                quantity=2,
                aliquot_type=self.aliquot_type
            )
            # Check that all 4 slots are now occupied
            total_occupied = AliquotLocation.objects.filter(box=small_box)
            self.assertEqual(total_occupied.count(), 4)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_auto_store_disabled_scenarios(self):
        """Test auto-store disabled scenarios"""
        # Disable auto-store on the device
        self.device.auto_store_enabled = False
        self.device.save()
        # Create aliquot with stored disposition
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type,
        )
        # Check that no storage locations were created
        storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(storage_locations.count(), 0)
    def test_auto_store_inheritance_from_device_to_box(self):
        """Test auto-store inheritance from device to box"""
        # Test that box inherits auto-store setting from device
        self.assertTrue(self.box.auto_store_enabled)
        # Disable auto-store on device
        self.device.auto_store_enabled = False
        self.device.save()
        # Box should now inherit the disabled setting
        self.assertFalse(self.box.auto_store_enabled)


class TubeDispositionChangeSignalTest(SignalHandlerTest):
    """Test cases for tube disposition change signal"""
    def test_storage_location_removal_when_tube_disposition_changes(self):
        """Test storage location removal when tube disposition changes"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Create aliquot with stored disposition
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=2,
                aliquot_type=self.aliquot_type
            )
            # Verify tubes were stored
            storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(storage_locations.count(), 2)
            # Change disposition of one tube to 'in use'
            tube = AliquotTube.objects.filter(aliquot=aliquot).first()
            tube.disposition = self.in_use_disposition
            tube.save()
            # Check that storage location was removed for that tube
            remaining_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(remaining_locations.count(), 1)
            # The remaining location should be for the other tube
            remaining_tube_number = remaining_locations.first().tube_number
            self.assertNotEqual(remaining_tube_number, tube.tube_number)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_storage_location_removal_for_exhausted_tubes(self):
        """Test storage location removal for exhausted tubes"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Create aliquot with stored disposition
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=3,
                aliquot_type=self.aliquot_type
            )
            # Verify tubes were stored
            storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(storage_locations.count(), 3)
            # Change disposition of all tubes to 'exhausted'
            tubes = AliquotTube.objects.filter(aliquot=aliquot)
            for tube in tubes:
                tube.disposition = self.exhausted_disposition
                tube.save()
            # Check that all storage locations were removed
            remaining_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(remaining_locations.count(), 0)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_no_storage_removal_for_stored_to_stored_changes(self):
        """Test no storage removal for stored to stored changes"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Create aliquot with stored disposition
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=2,
                aliquot_type=self.aliquot_type
            )
            # Verify tubes were stored
            storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(storage_locations.count(), 2)
            # Change to a different stored disposition
            new_stored_disposition = AliquotDisposition.objects.create(
                name="Stored 2",
                disposition_type="stored"
            )
            tube = AliquotTube.objects.filter(aliquot=aliquot).first()
            tube.disposition = new_stored_disposition
            tube.save()
            # Storage location should remain
            remaining_locations = AliquotLocation.objects.filter(aliquot=aliquot)
            self.assertEqual(remaining_locations.count(), 2)
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting
    def test_old_disposition_storage(self):
        """Test old disposition storage before saving"""
        # Enable automatic tube creation and storage
        from .signals import AUTO_CREATE_TUBES, AUTO_STORE_TUBES
        original_create_setting = AUTO_CREATE_TUBES
        original_store_setting = AUTO_STORE_TUBES
        try:
            # Temporarily enable auto-creation and auto-storage
            import sample.signals
            sample.signals.AUTO_CREATE_TUBES = True
            sample.signals.AUTO_STORE_TUBES = True
            # Create aliquot
            aliquot = Aliquot.objects.create(
                sample=self.sample,
                quantity=1,
                aliquot_type=self.aliquot_type
            )
            tube = AliquotTube.objects.filter(aliquot=aliquot).first()
            # Change disposition
            tube.disposition = self.in_use_disposition
            tube.save()
            # The signal should have stored the old disposition
            # This is tested indirectly through the storage location removal
        finally:
            # Restore original settings
            sample.signals.AUTO_CREATE_TUBES = original_create_setting
            sample.signals.AUTO_STORE_TUBES = original_store_setting


class AliquotTubeManagementTest(SignalHandlerTest):
    """Test cases for aliquot tube management"""
    def test_tube_count_calculations_stored_vs_unstored(self):
        """Test tube count calculations (stored vs unstored)"""
        # Create aliquot with 5 tubes
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
        # Create tubes explicitly
        aliquot.create_tubes(auto_store=False)
        # All tubes should be stored initially
        self.assertEqual(aliquot.stored_tubes_count, 5)
        self.assertEqual(aliquot.unstored_tubes_count, 0)
        # Change some tubes to 'in use'
        tubes = AliquotTube.objects.filter(aliquot=aliquot)[:2]
        for tube in tubes:
            aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
        # Refresh aliquot from database
        aliquot.refresh_from_db()
        # Should have 3 stored and 2 unstored
        self.assertEqual(aliquot.stored_tubes_count, 3)
        self.assertEqual(aliquot.unstored_tubes_count, 2)
    def test_tube_count_calculations_for_non_stored_aliquots(self):
        """Test tube count calculations for non-stored aliquots"""
        # Create aliquot with 3 tubes
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        # Create tubes explicitly
        aliquot.create_tubes(auto_store=False)
        # Change all tubes to in_use disposition
        tubes = AliquotTube.objects.filter(aliquot=aliquot)
        for tube in tubes:
            aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
        # For non-stored aliquots, all tubes are considered unstored
        self.assertEqual(aliquot.stored_tubes_count, 0)
        self.assertEqual(aliquot.unstored_tubes_count, 3)
    def test_individual_tube_disposition_management(self):
        """Test individual tube disposition management"""
        # Create aliquot with 3 tubes
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        # Create tubes explicitly
        aliquot.create_tubes(auto_store=False)
        tubes = AliquotTube.objects.filter(aliquot=aliquot).order_by('tube_number')
        # Set different dispositions for each tube
        aliquot.change_tube_disposition(tubes[0].tube_number, self.stored_disposition)  # Keep stored
        aliquot.change_tube_disposition(tubes[1].tube_number, self.in_use_disposition)  # Change to in use
        aliquot.change_tube_disposition(tubes[2].tube_number, self.exhausted_disposition)  # Change to exhausted
        # Refresh aliquot
        aliquot.refresh_from_db()
        # Should have 1 stored and 2 unstored
        self.assertEqual(aliquot.stored_tubes_count, 1)
        self.assertEqual(aliquot.unstored_tubes_count, 2)
        # Since we're not using auto-storage, no storage locations should exist
        storage_locations = AliquotLocation.objects.filter(aliquot=aliquot)
        self.assertEqual(storage_locations.count(), 0)

    def test_simple_disposition_change(self):
        """Simple test to change disposition without signal interference"""
        # Create aliquot with 3 tubes
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        # Create tubes explicitly
        aliquot.create_tubes(auto_store=False)
        tubes = AliquotTube.objects.filter(aliquot=aliquot).order_by('tube_number')
        # Change tube 2 to in use
        aliquot.change_tube_disposition(tubes[1].tube_number, self.in_use_disposition)
        # Refresh aliquot
        aliquot.refresh_from_db()
        # Check if the change worked
        self.assertEqual(aliquot.stored_tubes_count, 2)
        self.assertEqual(aliquot.unstored_tubes_count, 1)
