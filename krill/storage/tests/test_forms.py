from django.test import TestCase
from django import forms

from ..models.storage import Device, Shelf, Rack, Box
from ..models.site import Site
from ..forms import SiteForm, DeviceForm, ShelfForm, RackForm, BoxForm


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
        self.assertEqual(site.description, '')
    def test_site_form_widgets_and_help_texts(self):
        """Test site form widgets and help texts"""
        form = SiteForm()
        self.assertIn('Name of this site', str(form.fields['name'].help_text))
        self.assertIn('Description of this site', str(form.fields['description'].help_text))
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
            'site': 99999,
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
        self.assertEqual(device.description, '')
        self.assertFalse(device.auto_store_enabled)
    def test_device_form_auto_store_enabled_field(self):
        """Test device form auto_store_enabled field"""
        form_data = {
            'name': 'Auto-Store Device',
            'site': self.site.id,
            'auto_store_enabled': True
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        device = form.save()
        self.assertTrue(device.auto_store_enabled)
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
        self.assertIn('Name of this device', str(form.fields['name'].help_text))
        self.assertIn('Description of this device', str(form.fields['description'].help_text))
        self.assertIn('Site where this device is located', str(form.fields['site'].help_text))
        self.assertIn('Enable auto-store for all boxes in this device', str(form.fields['auto_store_enabled'].help_text))
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
            'device': 99999
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
        self.assertEqual(shelf.description, '')
    def test_shelf_form_widgets_and_help_texts(self):
        """Test shelf form widgets and help texts"""
        form = ShelfForm()
        self.assertIn('Name of this shelf', str(form.fields['name'].help_text))
        self.assertIn('Description of this shelf', str(form.fields['description'].help_text))
        self.assertIn('Device where this shelf is located', str(form.fields['device'].help_text))
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
            'shelf': 99999
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
        self.assertEqual(rack.description, '')
    def test_rack_form_widgets_and_help_texts(self):
        """Test rack form widgets and help texts"""
        form = RackForm()
        self.assertIn('Name of this rack', str(form.fields['name'].help_text))
        self.assertIn('Description of this rack', str(form.fields['description'].help_text))
        self.assertIn('Shelf where this rack is located', str(form.fields['shelf'].help_text))
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
        form_data = {
            'name': 'Test Box',
            'description': 'A test box',
            'rack': self.rack.id,
            'rows': 999999999,
            'columns': 12
        }
        form = BoxForm(data=form_data)
        self.assertTrue(form.is_valid())
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
        self.assertEqual(box.description, '')
    def test_box_form_widgets_and_help_texts(self):
        """Test box form widgets and help texts"""
        form = BoxForm()
        self.assertIn('Name of this box', str(form.fields['name'].help_text))
        self.assertIn('Description of this box', str(form.fields['description'].help_text))
        self.assertIn('Rack where this box is located', str(form.fields['rack'].help_text))
        self.assertIn('Number of rows in this box', str(form.fields['rows'].help_text))
        self.assertIn('Number of columns in this box', str(form.fields['columns'].help_text))
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)
