from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from .models.storage import Device, Shelf, Rack, Box
from .models.site import Site
from sample.models.sample import Sample
from sample.models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition, 
    AliquotLocation, AliquotTube
)
from sample.models.source import Source


class DeviceModelTest(TestCase):
    """Test cases for the Device model"""
    
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(
            name="Test Site",
            description="A test site"
        )
    
    def test_device_creation_with_auto_store_settings(self):
        """Test device creation with auto-store settings"""
        device = Device.objects.create(
            name="Test Device",
            description="A test device",
            site=self.site,
            auto_store_enabled=True
        )
        
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.description, "A test device")
        self.assertEqual(device.site, self.site)
        self.assertTrue(device.auto_store_enabled)
        self.assertIsNotNone(device.id)
    
    def test_device_creation_without_auto_store(self):
        """Test device creation without auto-store enabled"""
        device = Device.objects.create(
            name="Test Device 2",
            description="A test device without auto-store",
            site=self.site,
            auto_store_enabled=False
        )
        
        self.assertFalse(device.auto_store_enabled)
    
    def test_device_string_representation(self):
        """Test device string representation"""
        device = Device.objects.create(
            name="Test Device 3",
            site=self.site
        )
        
        self.assertEqual(str(device), "Test Device 3")
    
    def test_device_site_relationship_integrity(self):
        """Test device-site relationship integrity"""
        device = Device.objects.create(
            name="Test Device 4",
            site=self.site
        )
        
        self.assertEqual(device.site, self.site)
        self.assertIn(device, self.site.devices.all())
    
    def test_auto_store_enabled_field_functionality(self):
        """Test auto_store_enabled field functionality"""
        # Test with auto-store enabled
        device_enabled = Device.objects.create(
            name="Auto-Store Enabled Device",
            site=self.site,
            auto_store_enabled=True
        )
        self.assertTrue(device_enabled.auto_store_enabled)
        
        # Test with auto-store disabled
        device_disabled = Device.objects.create(
            name="Auto-Store Disabled Device",
            site=self.site,
            auto_store_enabled=False
        )
        self.assertFalse(device_disabled.auto_store_enabled)
        
        # Test changing auto-store setting
        device_disabled.auto_store_enabled = True
        device_disabled.save()
        self.assertTrue(device_disabled.auto_store_enabled)


class BoxModelTest(TestCase):
    """Test cases for the Box model"""
    
    def setUp(self):
        """Set up test data"""
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
    
    def test_box_creation_with_dimensions(self):
        """Test box creation with dimensions"""
        box = Box.objects.create(
            name="Test Box",
            description="A test box",
            rack=self.rack,
            rows=8,
            columns=12
        )
        
        self.assertEqual(box.name, "Test Box")
        self.assertEqual(box.description, "A test box")
        self.assertEqual(box.rack, self.rack)
        self.assertEqual(box.rows, 8)
        self.assertEqual(box.columns, 12)
        self.assertIsNotNone(box.id)
    
    def test_box_auto_store_inheritance_from_device(self):
        """Test box auto-store inheritance from device"""
        # Create device with auto-store enabled
        auto_store_device = Device.objects.create(
            name="Auto-Store Device",
            site=self.site,
            auto_store_enabled=True
        )
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
            rows=10,
            columns=10
        )
        
        # Box should inherit auto-store from device
        self.assertTrue(auto_store_box.auto_store_enabled)
        
        # Create device with auto-store disabled
        no_auto_store_device = Device.objects.create(
            name="No Auto-Store Device",
            site=self.site,
            auto_store_enabled=False
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
            rows=10,
            columns=10
        )
        
        # Box should inherit auto-store disabled from device
        self.assertFalse(no_auto_store_box.auto_store_enabled)
    
    def test_box_available_slots_calculation(self):
        """Test box available slots calculation"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=3,
            columns=3
        )
        
        # Initially all slots should be available
        available_slots = box.get_available_slots()
        self.assertEqual(len(available_slots), 9)  # 3x3 = 9 slots
        
        # Verify all coordinates are present
        expected_slots = [
            {'row': 1, 'column': 1}, {'row': 1, 'column': 2}, {'row': 1, 'column': 3},
            {'row': 2, 'column': 1}, {'row': 2, 'column': 2}, {'row': 2, 'column': 3},
            {'row': 3, 'column': 1}, {'row': 3, 'column': 2}, {'row': 3, 'column': 3}
        ]
        
        for expected_slot in expected_slots:
            self.assertIn(expected_slot, available_slots)
    
    def test_box_available_slots_with_occupied_slots(self):
        """Test box available slots calculation with occupied slots"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=2,
            columns=2
        )
        
        # Create test data for storage
        source = Source.objects.create(name="Test Source")
        sample = Sample.objects.create(name="Test Sample", source=source)
        aliquot_type = AliquotType.objects.create(name="Test Type")
        disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            dispositionType="stored"
        )
        aliquot = Aliquot.objects.create(
            sample=sample,
            quantity=2,
            aliquotType=aliquot_type
        )
        
        # Occupy slot (1, 1)
        AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=1,
            column=1,
            tube_number=1
        )
        
        # Check available slots
        available_slots = box.get_available_slots()
        self.assertEqual(len(available_slots), 3)  # 4 total - 1 occupied = 3
        
        # Verify remaining slots
        expected_remaining = [
            {'row': 1, 'column': 2},
            {'row': 2, 'column': 1},
            {'row': 2, 'column': 2}
        ]
        
        for expected_slot in expected_remaining:
            self.assertIn(expected_slot, available_slots)
        
        # Verify occupied slot is not available
        occupied_slot = {'row': 1, 'column': 1}
        self.assertNotIn(occupied_slot, available_slots)
    
    def test_box_capacity_validation(self):
        """Test box capacity validation"""
        # Test with valid dimensions
        valid_box = Box.objects.create(
            name="Valid Box",
            rack=self.rack,
            rows=1,
            columns=1
        )
        self.assertEqual(valid_box.rows, 1)
        self.assertEqual(valid_box.columns, 1)
        
        # Test with larger dimensions
        large_box = Box.objects.create(
            name="Large Box",
            rack=self.rack,
            rows=100,
            columns=100
        )
        self.assertEqual(large_box.rows, 100)
        self.assertEqual(large_box.columns, 100)
    
    def test_box_string_representation(self):
        """Test box string representation"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=10,
            columns=10
        )
        
        self.assertEqual(str(box), "Test Box")
    
    def test_box_rack_relationship_integrity(self):
        """Test box-rack relationship integrity"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=10,
            columns=10
        )
        
        self.assertEqual(box.rack, self.rack)
        self.assertIn(box, self.rack.boxes.all())
    
    def test_box_has_available_slots(self):
        """Test box has_available_slots method"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=2,
            columns=2
        )
        
        # Initially should have available slots
        self.assertTrue(box.has_available_slots())
        
        # Fill all slots
        source = Source.objects.create(name="Test Source")
        sample = Sample.objects.create(name="Test Sample", source=source)
        aliquot_type = AliquotType.objects.create(name="Test Type")
        disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            dispositionType="stored"
        )
        aliquot = Aliquot.objects.create(
            sample=sample,
            quantity=4,
            aliquotType=aliquot_type
        )
        
        # Occupy all slots
        for row in range(1, 3):
            for col in range(1, 3):
                AliquotLocation.objects.create(
                    aliquot=aliquot,
                    box=box,
                    row=row,
                    column=col,
                    tube_number=row * 2 + col
                )
        
        # Should not have available slots
        self.assertFalse(box.has_available_slots())
    
    def test_box_aliquots_property(self):
        """Test box aliquots property"""
        box = Box.objects.create(
            name="Test Box",
            rack=self.rack,
            rows=10,
            columns=10
        )
        
        # Initially no aliquots
        self.assertEqual(len(box.aliquots), 0)
        
        # Add some aliquots
        source = Source.objects.create(name="Test Source")
        sample = Sample.objects.create(name="Test Sample", source=source)
        aliquot_type = AliquotType.objects.create(name="Test Type")
        disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            dispositionType="stored"
        )
        aliquot = Aliquot.objects.create(
            sample=sample,
            quantity=2,
            aliquotType=aliquot_type
        )
        
        # Create storage locations
        AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=1,
            column=1,
            tube_number=1
        )
        AliquotLocation.objects.create(
            aliquot=aliquot,
            box=box,
            row=1,
            column=2,
            tube_number=2
        )
        
        # Should have 2 aliquot locations
        self.assertEqual(len(box.aliquots), 2)


class StorageHierarchyTest(TestCase):
    """Test cases for storage hierarchy integrity"""
    
    def setUp(self):
        """Set up test data"""
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
            rows=10,
            columns=10
        )
    
    def test_site_device_shelf_rack_box_hierarchy_integrity(self):
        """Test site-device-shelf-rack-box hierarchy integrity"""
        # Test forward navigation
        self.assertEqual(self.box.rack, self.rack)
        self.assertEqual(self.rack.shelf, self.shelf)
        self.assertEqual(self.shelf.device, self.device)
        self.assertEqual(self.device.site, self.site)
        
        # Test reverse navigation
        self.assertIn(self.device, self.site.devices.all())
        self.assertIn(self.shelf, self.device.shelves.all())
        self.assertIn(self.rack, self.shelf.racks.all())
        self.assertIn(self.box, self.rack.boxes.all())
    
    def test_storage_location_navigation(self):
        """Test storage location navigation (device → shelf → rack → box)"""
        # Test navigation from box to device
        device_from_box = self.box.rack.shelf.device
        self.assertEqual(device_from_box, self.device)
        
        # Test navigation from device to box
        boxes_from_device = self.device.shelves.first().racks.first().boxes.all()
        self.assertIn(self.box, boxes_from_device)
    
    def test_storage_capacity_calculations_across_hierarchy(self):
        """Test storage capacity calculations across hierarchy"""
        # Create multiple boxes with different capacities
        box1 = Box.objects.create(
            name="Box 1",
            rack=self.rack,
            rows=5,
            columns=5
        )
        box2 = Box.objects.create(
            name="Box 2",
            rack=self.rack,
            rows=3,
            columns=3
        )
        
        # Calculate total capacity at rack level
        rack_total_capacity = sum(box.rows * box.columns for box in self.rack.boxes.all())
        expected_rack_capacity = (10 * 10) + (5 * 5) + (3 * 3)  # 100 + 25 + 9 = 134
        self.assertEqual(rack_total_capacity, expected_rack_capacity)
        
        # Calculate total capacity at shelf level
        shelf_total_capacity = sum(
            box.rows * box.columns 
            for rack in self.shelf.racks.all() 
            for box in rack.boxes.all()
        )
        self.assertEqual(shelf_total_capacity, expected_rack_capacity)
        
        # Calculate total capacity at device level
        device_total_capacity = sum(
            box.rows * box.columns 
            for shelf in self.device.shelves.all()
            for rack in shelf.racks.all()
            for box in rack.boxes.all()
        )
        self.assertEqual(device_total_capacity, expected_rack_capacity)
        
        # Calculate total capacity at site level
        site_total_capacity = sum(
            box.rows * box.columns 
            for device in self.site.devices.all()
            for shelf in device.shelves.all()
            for rack in shelf.racks.all()
            for box in rack.boxes.all()
        )
        self.assertEqual(site_total_capacity, expected_rack_capacity)


class ShelfModelTest(TestCase):
    """Test cases for the Shelf model"""
    
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site
        )
    
    def test_shelf_creation(self):
        """Test shelf creation"""
        shelf = Shelf.objects.create(
            name="Test Shelf",
            description="A test shelf",
            device=self.device
        )
        
        self.assertEqual(shelf.name, "Test Shelf")
        self.assertEqual(shelf.description, "A test shelf")
        self.assertEqual(shelf.device, self.device)
        self.assertIsNotNone(shelf.id)
    
    def test_shelf_string_representation(self):
        """Test shelf string representation"""
        shelf = Shelf.objects.create(
            name="Test Shelf",
            device=self.device
        )
        
        self.assertEqual(str(shelf), "Test Shelf")
    
    def test_shelf_device_relationship_integrity(self):
        """Test shelf-device relationship integrity"""
        shelf = Shelf.objects.create(
            name="Test Shelf",
            device=self.device
        )
        
        self.assertEqual(shelf.device, self.device)
        self.assertIn(shelf, self.device.shelves.all())


class RackModelTest(TestCase):
    """Test cases for the Rack model"""
    
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site
        )
        self.shelf = Shelf.objects.create(
            name="Test Shelf",
            device=self.device
        )
    
    def test_rack_creation(self):
        """Test rack creation"""
        rack = Rack.objects.create(
            name="Test Rack",
            description="A test rack",
            shelf=self.shelf
        )
        
        self.assertEqual(rack.name, "Test Rack")
        self.assertEqual(rack.description, "A test rack")
        self.assertEqual(rack.shelf, self.shelf)
        self.assertIsNotNone(rack.id)
    
    def test_rack_string_representation(self):
        """Test rack string representation"""
        rack = Rack.objects.create(
            name="Test Rack",
            shelf=self.shelf
        )
        
        self.assertEqual(str(rack), "Test Rack")
    
    def test_rack_shelf_relationship_integrity(self):
        """Test rack-shelf relationship integrity"""
        rack = Rack.objects.create(
            name="Test Rack",
            shelf=self.shelf
        )
        
        self.assertEqual(rack.shelf, self.shelf)
        self.assertIn(rack, self.shelf.racks.all())


class SiteModelTest(TestCase):
    """Test cases for the Site model"""
    
    def test_site_creation(self):
        """Test site creation"""
        site = Site.objects.create(
            name="Test Site",
            description="A test site"
        )
        
        self.assertEqual(site.name, "Test Site")
        self.assertEqual(site.description, "A test site")
        self.assertIsNotNone(site.id)
    
    def test_site_string_representation(self):
        """Test site string representation"""
        site = Site.objects.create(name="Test Site")
        
        self.assertEqual(str(site), "Test Site")
    
    def test_site_device_relationship_integrity(self):
        """Test site-device relationship integrity"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(
            name="Test Device",
            site=site
        )
        
        self.assertEqual(device.site, site)
        self.assertIn(device, site.devices.all())
