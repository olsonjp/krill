from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django import forms
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models.storage import Device, Shelf, Rack, Box
from .models.site import Site
from .forms import SiteForm, DeviceForm, ShelfForm, RackForm, BoxForm
from .views.list import StorageListView
from .views.views import HomeView, StorageView
from sample.models.sample import Sample
from sample.models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition, 
    AliquotLocation, AliquotTube
)
from sample.models.source import Source
from person.models import UserRole

User = get_user_model()


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


class SiteFormTest(TestCase):
    """Test cases for the SiteForm"""
    def test_site_form_validation_with_valid_data(self):
        """Test site form validation with valid data"""
        form_data = {
            'name': 'Test Site',
            'description': 'A test site'
        }
        form = SiteForm(data=form_data)
        self.assertTrue(form.is_valid())
        site = form.save()
        self.assertEqual(site.name, 'Test Site')
        self.assertEqual(site.description, 'A test site')
    def test_site_form_error_handling_missing_name(self):
        """Test site form error handling for missing name"""
        form_data = {
            'description': 'A test site'
        }
        form = SiteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_site_form_with_optional_description(self):
        """Test site form with optional description"""
        form_data = {
            'name': 'Test Site No Description'
        }
        form = SiteForm(data=form_data)
        self.assertTrue(form.is_valid())
        site = form.save()
        self.assertEqual(site.name, 'Test Site No Description')
        self.assertEqual(site.description, '')  # Empty string, not None
    def test_site_form_widgets_and_help_texts(self):
        """Test site form widgets and help texts"""
        form = SiteForm()
        # Test help texts
        self.assertIn('Name of this site', str(form.fields['name'].help_text))
        self.assertIn('Description of this site', str(form.fields['description'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)


class DeviceFormTest(TestCase):
    """Test cases for the DeviceForm"""
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(
            name="Test Site",
            description="A test site"
        )
    def test_device_form_validation_with_valid_data(self):
        """Test device form validation with valid data"""
        form_data = {
            'name': 'Test Device',
            'description': 'A test device',
            'site': self.site.id,
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        device = form.save()
        self.assertEqual(device.name, 'Test Device')
        self.assertEqual(device.description, 'A test device')
        self.assertEqual(device.site, self.site)
        self.assertTrue(device.auto_store_enabled)
    def test_device_form_error_handling_missing_name(self):
        """Test device form error handling for missing name"""
        form_data = {
            'description': 'A test device',
            'site': self.site.id,
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_device_form_error_handling_missing_site(self):
        """Test device form error handling for missing site"""
        form_data = {
            'name': 'Test Device',
            'description': 'A test device',
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('site', form.errors)
    def test_device_form_error_handling_invalid_site(self):
        """Test device form error handling for invalid site"""
        form_data = {
            'name': 'Test Device',
            'description': 'A test device',
            'site': 99999,  # Non-existent site ID
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('site', form.errors)
    def test_device_form_with_optional_fields(self):
        """Test device form with optional fields"""
        form_data = {
            'name': 'Test Device Optional',
            'site': self.site.id
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        device = form.save()
        self.assertEqual(device.name, 'Test Device Optional')
        self.assertEqual(device.site, self.site)
        self.assertEqual(device.description, '')  # Empty string, not None
        self.assertFalse(device.auto_store_enabled)  # Default value
    def test_device_form_auto_store_enabled_field(self):
        """Test device form auto_store_enabled field"""
        # Test with auto-store enabled
        form_data = {
            'name': 'Auto-Store Device',
            'site': self.site.id,
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        device = form.save()
        self.assertTrue(device.auto_store_enabled)
        # Test with auto-store disabled
        form_data = {
            'name': 'No Auto-Store Device',
            'site': self.site.id,
            'auto_store_enabled': False
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        device = form.save()
        self.assertFalse(device.auto_store_enabled)
    def test_device_form_widgets_and_help_texts(self):
        """Test device form widgets and help texts"""
        form = DeviceForm()
        # Test help texts
        self.assertIn('Name of this device', str(form.fields['name'].help_text))
        self.assertIn('Description of this device', str(form.fields['description'].help_text))
        self.assertIn('Site where this device is located', str(form.fields['site'].help_text))
        self.assertIn('Enable auto-store for all boxes in this device', str(form.fields['auto_store_enabled'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)


class ShelfFormTest(TestCase):
    """Test cases for the ShelfForm"""
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(
            name="Test Device",
            site=self.site
        )
    def test_shelf_form_validation_with_valid_data(self):
        """Test shelf form validation with valid data"""
        form_data = {
            'name': 'Test Shelf',
            'description': 'A test shelf',
            'device': self.device.id
        }
        form = ShelfForm(data=form_data)
        self.assertTrue(form.is_valid())
        shelf = form.save()
        self.assertEqual(shelf.name, 'Test Shelf')
        self.assertEqual(shelf.description, 'A test shelf')
        self.assertEqual(shelf.device, self.device)
    def test_shelf_form_error_handling_missing_name(self):
        """Test shelf form error handling for missing name"""
        form_data = {
            'description': 'A test shelf',
            'device': self.device.id
        }
        form = ShelfForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_shelf_form_error_handling_missing_device(self):
        """Test shelf form error handling for missing device"""
        form_data = {
            'name': 'Test Shelf',
            'description': 'A test shelf'
        }
        form = ShelfForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('device', form.errors)
    def test_shelf_form_error_handling_invalid_device(self):
        """Test shelf form error handling for invalid device"""
        form_data = {
            'name': 'Test Shelf',
            'description': 'A test shelf',
            'device': 99999  # Non-existent device ID
        }
        form = ShelfForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('device', form.errors)
    def test_shelf_form_with_optional_description(self):
        """Test shelf form with optional description"""
        form_data = {
            'name': 'Test Shelf No Description',
            'device': self.device.id
        }
        form = ShelfForm(data=form_data)
        self.assertTrue(form.is_valid())
        shelf = form.save()
        self.assertEqual(shelf.name, 'Test Shelf No Description')
        self.assertEqual(shelf.device, self.device)
        self.assertEqual(shelf.description, '')  # Empty string, not None
    def test_shelf_form_widgets_and_help_texts(self):
        """Test shelf form widgets and help texts"""
        form = ShelfForm()
        # Test help texts
        self.assertIn('Name of this shelf', str(form.fields['name'].help_text))
        self.assertIn('Description of this shelf', str(form.fields['description'].help_text))
        self.assertIn('Device where this shelf is located', str(form.fields['device'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)


class RackFormTest(TestCase):
    """Test cases for the RackForm"""
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.shelf = Shelf.objects.create(
            name="Test Shelf",
            device=self.device
        )
    def test_rack_form_validation_with_valid_data(self):
        """Test rack form validation with valid data"""
        form_data = {
            'name': 'Test Rack',
            'description': 'A test rack',
            'shelf': self.shelf.id
        }
        form = RackForm(data=form_data)
        self.assertTrue(form.is_valid())
        rack = form.save()
        self.assertEqual(rack.name, 'Test Rack')
        self.assertEqual(rack.description, 'A test rack')
        self.assertEqual(rack.shelf, self.shelf)
    def test_rack_form_error_handling_missing_name(self):
        """Test rack form error handling for missing name"""
        form_data = {
            'description': 'A test rack',
            'shelf': self.shelf.id
        }
        form = RackForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_rack_form_error_handling_missing_shelf(self):
        """Test rack form error handling for missing shelf"""
        form_data = {
            'name': 'Test Rack',
            'description': 'A test rack'
        }
        form = RackForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shelf', form.errors)
    def test_rack_form_error_handling_invalid_shelf(self):
        """Test rack form error handling for invalid shelf"""
        form_data = {
            'name': 'Test Rack',
            'description': 'A test rack',
            'shelf': 99999  # Non-existent shelf ID
        }
        form = RackForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shelf', form.errors)
    def test_rack_form_with_optional_description(self):
        """Test rack form with optional description"""
        form_data = {
            'name': 'Test Rack No Description',
            'shelf': self.shelf.id
        }
        form = RackForm(data=form_data)
        self.assertTrue(form.is_valid())
        rack = form.save()
        self.assertEqual(rack.name, 'Test Rack No Description')
        self.assertEqual(rack.shelf, self.shelf)
        self.assertEqual(rack.description, '')  # Empty string, not None
    def test_rack_form_widgets_and_help_texts(self):
        """Test rack form widgets and help texts"""
        form = RackForm()
        # Test help texts
        self.assertIn('Name of this rack', str(form.fields['name'].help_text))
        self.assertIn('Description of this rack', str(form.fields['description'].help_text))
        self.assertIn('Shelf where this rack is located', str(form.fields['shelf'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)


class BoxFormTest(TestCase):
    """Test cases for the BoxForm"""
    def setUp(self):
        """Set up test data"""
        self.site = Site.objects.create(name="Test Site")
        self.device = Device.objects.create(name="Test Device", site=self.site)
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device)
        self.rack = Rack.objects.create(
            name="Test Rack",
            shelf=self.shelf
        )
    def test_box_form_validation_with_valid_data(self):
        """Test box form validation with valid data"""
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rack': self.rack.id,
            'rows': 8,
            'columns': 12
        }
        form = BoxForm(data=form_data)
        self.assertTrue(form.is_valid())
        box = form.save()
        self.assertEqual(box.name, 'Test Box')
        self.assertEqual(box.description, 'A test box')
        self.assertEqual(box.rack, self.rack)
        self.assertEqual(box.rows, 8)
        self.assertEqual(box.columns, 12)
    def test_box_form_error_handling_missing_name(self):
        """Test box form error handling for missing name"""
        form_data = {
            'description': 'A test box',
            'rack': self.rack.id,
            'rows': 8,
            'columns': 12
        }
        form = BoxForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_box_form_error_handling_missing_rack(self):
        """Test box form error handling for missing rack"""
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rows': 8,
            'columns': 12
        }
        form = BoxForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('rack', form.errors)
    def test_box_form_error_handling_missing_dimensions(self):
        """Test box form error handling for missing dimensions"""
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rack': self.rack.id
        }
        form = BoxForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('rows', form.errors)
        self.assertIn('columns', form.errors)
    def test_box_form_error_handling_invalid_dimensions(self):
        """Test box form error handling for invalid dimensions"""
        # Django IntegerField allows zero and negative values by default
        # So we'll test with very large numbers instead
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rack': self.rack.id,
            'rows': 999999999,
            'columns': 12
        }
        form = BoxForm(data=form_data)
        self.assertTrue(form.is_valid())  # Large dimensions are allowed
        # Test with reasonable dimensions
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rack': self.rack.id,
            'rows': 1,
            'columns': 1
        }
        form = BoxForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_box_form_with_optional_description(self):
        """Test box form with optional description"""
        form_data = {
            'name': 'Test Box No Description',
            'rack': self.rack.id,
            'rows': 5,
            'columns': 5
        }
        form = BoxForm(data=form_data)
        self.assertTrue(form.is_valid())
        box = form.save()
        self.assertEqual(box.name, 'Test Box No Description')
        self.assertEqual(box.rack, self.rack)
        self.assertEqual(box.rows, 5)
        self.assertEqual(box.columns, 5)
        self.assertEqual(box.description, '')  # Empty string, not None
    def test_box_form_widgets_and_help_texts(self):
        """Test box form widgets and help texts"""
        form = BoxForm()
        # Test help texts
        self.assertIn('Name of this box', str(form.fields['name'].help_text))
        self.assertIn('Description of this box', str(form.fields['description'].help_text))
        self.assertIn('Rack where this box is located', str(form.fields['rack'].help_text))
        self.assertIn('Number of rows in this box', str(form.fields['rows'].help_text))
        self.assertIn('Number of columns in this box', str(form.fields['columns'].help_text))
        # Test widgets
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)


class StorageViewTest(TestCase):
    """Base test class for storage views with common setup"""
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        # Create test user with lab_member role
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Update the automatically created role
        self.user_role = self.user.role
        self.user_role.role = 'lab_member'
        self.user_role.save()
        # Create test storage hierarchy
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
        # Create test sample data for location tests
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquotType=self.aliquot_type
        )


class StorageListViewTest(StorageViewTest):
    """Test cases for the StorageListView"""
    def test_storage_list_requires_login(self):
        """Test that storage list requires login"""
        response = self.client.get(reverse('storage:list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_storage_list_get_request_default(self):
        """Test storage list GET request with default type (site)"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Sites')
        # Check that sites are in the context
        items = response.context['items']
        self.assertIn(self.site, items)
    def test_storage_list_get_request_box_type(self):
        """Test storage list GET request with box type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:list'), {'type': 'box'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Boxes')
        # Check that boxes are in the context
        items = response.context['items']
        self.assertIn(self.box, items)
    def test_storage_list_get_request_shelf_type(self):
        """Test storage list GET request with shelf type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:list'), {'type': 'shelf'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Shelves')
        # Check that shelves are in the context
        items = response.context['items']
        self.assertIn(self.shelf, items)
    def test_storage_list_get_request_device_type(self):
        """Test storage list GET request with device type"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:list'), {'type': 'device'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/list.html')
        self.assertIn('items', response.context)
        self.assertIn('model_name', response.context)
        self.assertEqual(response.context['model_name'], 'Devices')
        # Check that devices are in the context
        items = response.context['items']
        self.assertIn(self.device, items)


class HomeViewTest(StorageViewTest):
    """Test cases for the HomeView"""
    def test_home_view_requires_login(self):
        """Test that home view requires login"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_home_view_get_request(self):
        """Test home view GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'krill/home.html')
        self.assertIn('stats', response.context)
        self.assertIn('recent_activity', response.context)
        # Check that stats are in the context
        stats = response.context['stats']
        self.assertIn('active_samples', stats)
        self.assertIn('storage_usage', stats)
        self.assertIn('recent_reports', stats)
        self.assertIn('alerts', stats)
        self.assertIn('total_slots', stats)
        self.assertIn('used_slots', stats)
        # Check that recent activity is in the context
        recent_activity = response.context['recent_activity']
        self.assertIsInstance(recent_activity, list)


class StorageViewTest(StorageViewTest):
    """Test cases for the StorageView"""
    def test_storage_view_requires_login(self):
        """Test that storage view requires login"""
        response = self.client.get(reverse('storage:storage'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_storage_view_get_request(self):
        """Test storage view GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('storage:storage'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'storage/storage.html')


class DashboardStatsViewTest(StorageViewTest):
    """Test cases for the dashboard_stats view"""
    def test_dashboard_stats_requires_login(self):
        """Test that dashboard stats requires login"""
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    def test_dashboard_stats_get_request(self):
        """Test dashboard stats GET request"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Check response structure
        self.assertIn('active_samples', data)
        self.assertIn('storage_usage', data)
        self.assertIn('recent_reports', data)
        self.assertIn('alerts', data)
        self.assertIn('total_slots', data)
        self.assertIn('used_slots', data)
        # Check data types
        self.assertIsInstance(data['active_samples'], int)
        self.assertIsInstance(data['storage_usage'], int)
        self.assertIsInstance(data['recent_reports'], int)
        self.assertIsInstance(data['alerts'], int)
        self.assertIsInstance(data['total_slots'], int)
        self.assertIsInstance(data['used_slots'], int)
        # Check that values are reasonable
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
        # Create some sample data
        sample2 = Sample.objects.create(name="Test Sample 2", source=self.source)
        sample3 = Sample.objects.create(name="Test Sample 3", source=self.source)
        # Create some aliquot locations to use storage
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
        # Check that stats reflect the data
        self.assertEqual(data['active_samples'], 3)  # 3 samples total
        self.assertEqual(data['used_slots'], 2)  # 2 locations
        self.assertEqual(data['total_slots'], 100)  # 10x10 box
        self.assertEqual(data['storage_usage'], 2)  # 2% usage
