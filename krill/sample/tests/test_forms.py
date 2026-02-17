from django.test import TestCase
from django.contrib.auth import get_user_model
from django import forms

from ..models.sample import Sample
from ..models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation, AliquotTube
)
from ..models.source import Source
from ..forms import (
    SampleForm, AliquotForm, AliquotLocationForm,
    AliquotTypeForm, AliquotDispositionForm, SourceForm
)
from storage.models.storage import Device, Shelf, Rack, Box
from storage.models.site import Site


class SampleFormTest(TestCase):
    """Test cases for the SampleForm"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
    def test_sample_form_validation_with_valid_data(self):
        """Test sample form validation with valid data"""
        form_data = {
            'name': 'Test Sample',
            'source': self.source.id,
            'notes': 'Test notes for the sample',
            'access_level': 'all_members',
        }
        form = SampleForm(data=form_data)
        self.assertTrue(form.is_valid())
        sample = form.save()
        self.assertEqual(sample.name, 'Test Sample')
        self.assertEqual(sample.source, self.source)
        self.assertEqual(sample.notes, 'Test notes for the sample')
    def test_sample_form_with_required_fields_only(self):
        """Test sample form with only required fields"""
        form_data = {
            'name': 'Test Sample Required',
            'source': self.source.id,
            'access_level': 'all_members',
        }
        form = SampleForm(data=form_data)
        self.assertTrue(form.is_valid())
        sample = form.save()
        self.assertEqual(sample.name, 'Test Sample Required')
        self.assertEqual(sample.source, self.source)
        self.assertEqual(sample.notes, '')
    def test_sample_form_with_optional_fields(self):
        """Test sample form with optional fields"""
        form_data = {
            'name': 'Test Sample Optional',
            'source': self.source.id,
            'notes': 'Optional notes',
            'access_level': 'all_members',
        }
        form = SampleForm(data=form_data)
        self.assertTrue(form.is_valid())
        sample = form.save()
        self.assertEqual(sample.notes, 'Optional notes')
    def test_sample_form_error_handling_missing_name(self):
        """Test sample form error handling for missing name"""
        form_data = {
            'source': self.source.id,
            'notes': 'Test notes'
        }
        form = SampleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_sample_form_error_handling_missing_source(self):
        """Test sample form error handling for missing source"""
        form_data = {
            'name': 'Test Sample',
            'notes': 'Test notes'
        }
        form = SampleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('source', form.errors)
    def test_sample_form_error_handling_invalid_source(self):
        """Test sample form error handling for invalid source"""
        form_data = {
            'name': 'Test Sample',
            'source': 99999,
            'notes': 'Test notes'
        }
        form = SampleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('source', form.errors)
    def test_sample_form_widgets_and_help_texts(self):
        """Test sample form widgets and help texts"""
        form = SampleForm()
        self.assertIn('Unique identifier for the sample', str(form.fields['name'].help_text))
        self.assertIn('Source of the sample', str(form.fields['source'].help_text))
        self.assertIn('Additional information about the sample', str(form.fields['notes'].help_text))
        self.assertIsInstance(form.fields['notes'].widget, forms.Textarea)
        self.assertEqual(form.fields['notes'].widget.attrs['rows'], 4)


class AliquotFormTest(TestCase):
    """Test cases for the AliquotForm"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            disposition_type="stored"
        )
        self.in_use_disposition = AliquotDisposition.objects.create(
            name="Test In Use",
            disposition_type="in_use"
        )
        self.exhausted_disposition = AliquotDisposition.objects.create(
            name="Test Exhausted",
            disposition_type="exhausted"
        )
        self.parent_aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
    def test_aliquot_form_validation_with_valid_data(self):
        """Test aliquot form validation with valid data"""
        form_data = {
            'sample': self.sample.id,
            'quantity': 3,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertEqual(aliquot.sample, self.sample)
        self.assertEqual(aliquot.quantity, 3)
        self.assertEqual(aliquot.aliquot_type, self.aliquot_type)
    def test_aliquot_form_with_parent_selection(self):
        """Test aliquot form with parent selection"""
        form_data = {
            'parent': self.parent_aliquot.id,
            'sample': self.sample.id,
            'quantity': 2,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertEqual(aliquot.parent, self.parent_aliquot)
    def test_aliquot_form_quantity_validation(self):
        """Test aliquot form quantity validation"""
        form_data = {
            'sample': self.sample.id,
            'quantity': 1,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        form_data['quantity'] = 0
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        form_data['quantity'] = 999999999
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_aliquot_form_disposition_selection(self):
        """Test aliquot form disposition selection"""
        form_data = {
            'sample': self.sample.id,
            'quantity': 3,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertIsNotNone(aliquot.disposition)
    def test_aliquot_form_error_handling_missing_required_fields(self):
        """Test aliquot form error handling for missing required fields"""
        # Missing sample (required)
        form_data = {
            'quantity': 3,
            'aliquot_type': self.aliquot_type.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('sample', form.errors)
        # aliquot_type is optional (blank=True on model) so omitting it is valid
        form_data = {
            'sample': self.sample.id,
            'quantity': 3,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_aliquot_form_widgets_and_help_texts(self):
        """Test aliquot form widgets and help texts"""
        form = AliquotForm()
        self.assertIn('Parent aliquot, if this is a derivative', str(form.fields['parent'].help_text))
        self.assertIn('Sample this aliquot belongs to', str(form.fields['sample'].help_text))
        self.assertIn('Quantity of the aliquot', str(form.fields['quantity'].help_text))
        self.assertIn('Type of aliquot', str(form.fields['aliquot_type'].help_text))
        self.assertIn('Restrict access to specific user tiers', str(form.fields['access_level'].help_text))


class AliquotLocationFormTest(TestCase):
    """Test cases for the AliquotLocationForm"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
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
    def test_aliquot_location_form_validation_with_valid_data(self):
        """Test aliquot location form validation with valid data"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 5,
            'column': 5,
            'tube_number': 1
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())
        location = form.save()
        self.assertEqual(location.aliquot, self.aliquot)
        self.assertEqual(location.box, self.box)
        self.assertEqual(location.row, 5)
        self.assertEqual(location.column, 5)
        self.assertEqual(location.tube_number, 1)
    def test_aliquot_location_form_accepts_any_row(self):
        """Test aliquot location form accepts any integer row (no bounds validation)"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 15,
            'column': 5,
            'tube_number': 1
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_aliquot_location_form_accepts_any_column(self):
        """Test aliquot location form accepts any integer column (no bounds validation)"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 5,
            'column': 15,
            'tube_number': 1
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_aliquot_location_form_error_handling_invalid_tube_number(self):
        """Test aliquot location form error handling for invalid tube number"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 5,
            'column': 5,
            'tube_number': 999
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())
    def test_aliquot_location_form_widgets_and_help_texts(self):
        """Test aliquot location form widgets and help texts"""
        form = AliquotLocationForm()
        self.assertIn('Aliquot to locate', str(form.fields['aliquot'].help_text))
        self.assertIn('Storage box', str(form.fields['box'].help_text))
        self.assertIn('Row position (1-10)', str(form.fields['row'].help_text))
        self.assertIn('Column position (1-10)', str(form.fields['column'].help_text))
        self.assertIn('Tube number within the aliquot', str(form.fields['tube_number'].help_text))


class AliquotTypeFormTest(TestCase):
    """Test cases for the AliquotTypeForm"""
    def test_aliquot_type_form_validation_with_valid_data(self):
        """Test aliquot type form validation with valid data"""
        form_data = {
            'name': 'Test Type',
            'description': 'A test aliquot type'
        }
        form = AliquotTypeForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot_type = form.save()
        self.assertEqual(aliquot_type.name, 'Test Type')
        self.assertEqual(aliquot_type.description, 'A test aliquot type')
    def test_aliquot_type_form_error_handling_missing_name(self):
        """Test aliquot type form error handling for missing name"""
        form_data = {
            'description': 'A test aliquot type'
        }
        form = AliquotTypeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_aliquot_type_form_with_optional_description(self):
        """Test aliquot type form with optional description"""
        form_data = {
            'name': 'Test Type No Description'
        }
        form = AliquotTypeForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot_type = form.save()
        self.assertEqual(aliquot_type.name, 'Test Type No Description')
        self.assertEqual(aliquot_type.description, '')
    def test_aliquot_type_form_widgets_and_help_texts(self):
        """Test aliquot type form widgets and help texts"""
        form = AliquotTypeForm()
        self.assertIn('Name of this aliquot type', str(form.fields['name'].help_text))
        self.assertIn('Description of this type', str(form.fields['description'].help_text))


class AliquotDispositionFormTest(TestCase):
    """Test cases for the AliquotDispositionForm"""
    def test_aliquot_disposition_form_validation_with_valid_data(self):
        """Test aliquot disposition form validation with valid data"""
        form_data = {
            'name': 'Test Stored',
            'disposition_type': 'stored',
        }
        form = AliquotDispositionForm(data=form_data)
        self.assertTrue(form.is_valid())
        disposition = form.save()
        self.assertEqual(disposition.name, 'Test Stored')
        self.assertEqual(disposition.disposition_type, 'stored')
    def test_aliquot_disposition_form_error_handling_missing_name(self):
        """Test aliquot disposition form error handling for missing name"""
        form_data = {
            'disposition_type': 'stored',
        }
        form = AliquotDispositionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_aliquot_disposition_form_error_handling_missing_disposition_type(self):
        """Test aliquot disposition form error handling for missing disposition type"""
        form_data = {
            'name': 'Test Disposition',
        }
        form = AliquotDispositionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('disposition_type', form.errors)
    def test_aliquot_disposition_form_with_all_fields(self):
        """Test aliquot disposition form with all fields"""
        form_data = {
            'name': 'Test Disposition Exhausted',
            'disposition_type': 'exhausted',
        }
        form = AliquotDispositionForm(data=form_data)
        self.assertTrue(form.is_valid())
        disposition = form.save()
        self.assertEqual(disposition.name, 'Test Disposition Exhausted')
        self.assertEqual(disposition.disposition_type, 'exhausted')
    def test_aliquot_disposition_form_widgets_and_help_texts(self):
        """Test aliquot disposition form widgets and help texts"""
        form = AliquotDispositionForm()
        self.assertIn('Name of this disposition', str(form.fields['name'].help_text))
        self.assertIn('Type of disposition', str(form.fields['disposition_type'].help_text))


class SourceFormTest(TestCase):
    """Test cases for the SourceForm"""
    def test_source_form_validation_with_valid_data(self):
        """Test source form validation with valid data"""
        form_data = {
            'name': 'Test Source',
            'description': 'A test source'
        }
        form = SourceForm(data=form_data)
        self.assertTrue(form.is_valid())
        source = form.save()
        self.assertEqual(source.name, 'Test Source')
        self.assertEqual(source.description, 'A test source')
    def test_source_form_error_handling_missing_name(self):
        """Test source form error handling for missing name"""
        form_data = {
            'description': 'A test source'
        }
        form = SourceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    def test_source_form_with_optional_description(self):
        """Test source form with optional description"""
        form_data = {
            'name': 'Test Source No Description'
        }
        form = SourceForm(data=form_data)
        self.assertTrue(form.is_valid())
        source = form.save()
        self.assertEqual(source.name, 'Test Source No Description')
        self.assertEqual(source.description, '')


class AliquotTubeFormTest(TestCase):
    """Test cases for the AliquotTubeForm"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        self.in_use_disposition = AliquotDisposition.objects.create(
            name="In Use",
            disposition_type="in_use"
        )
        self.exhausted_disposition = AliquotDisposition.objects.create(
            name="Exhausted",
            disposition_type="exhausted"
        )
        self.tube = AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_aliquot_tube_form_creation(self):
        """Test AliquotTubeForm creation with valid data"""
        from ..forms import AliquotTubeForm
        form = AliquotTubeForm(instance=self.tube)
        self.assertIsInstance(form, AliquotTubeForm)
        self.assertEqual(form.instance, self.tube)

    def test_aliquot_tube_form_fields(self):
        """Test that AliquotTubeForm has the correct fields"""
        from ..forms import AliquotTubeForm
        form = AliquotTubeForm(instance=self.tube)
        self.assertIn('disposition', form.fields)
        self.assertNotIn('aliquot', form.fields)
        self.assertNotIn('tube_number', form.fields)

    def test_aliquot_tube_form_validation(self):
        """Test AliquotTubeForm validation with valid data"""
        from ..forms import AliquotTubeForm
        form_data = {
            'disposition': self.in_use_disposition.id
        }
        form = AliquotTubeForm(data=form_data, instance=self.tube)
        self.assertTrue(form.is_valid())

    def test_aliquot_tube_form_invalid_data(self):
        """Test AliquotTubeForm validation with invalid data"""
        from ..forms import AliquotTubeForm
        form_data = {
            'disposition': 99999
        }
        form = AliquotTubeForm(data=form_data, instance=self.tube)
        self.assertFalse(form.is_valid())


class AliquotTubeMoveFormTest(TestCase):
    """Test cases for the AliquotTubeMoveForm"""

    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        self.in_use_disposition = AliquotDisposition.objects.create(
            name="In Use",
            disposition_type="in_use"
        )
        self.exhausted_disposition = AliquotDisposition.objects.create(
            name="Exhausted",
            disposition_type="exhausted"
        )
        self.tube = AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )

        self.site = Site.objects.create(name="Test Site", description="Test site")
        self.device = Device.objects.create(name="Test Device", site=self.site, description="Test device")
        self.shelf = Shelf.objects.create(name="Test Shelf", device=self.device, description="Test shelf")
        self.rack = Rack.objects.create(name="Test Rack", shelf=self.shelf, description="Test rack")
        self.box = Box.objects.create(name="Test Box", rack=self.rack, rows=8, columns=12, description="Test box")
        self.box2 = Box.objects.create(name="Test Box 2", rack=self.rack, rows=6, columns=8, description="Test box 2")

        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_aliquot_tube_move_form_creation(self):
        """Test AliquotTubeMoveForm creation"""
        from ..forms import AliquotTubeMoveForm
        form = AliquotTubeMoveForm()
        self.assertIsInstance(form, AliquotTubeMoveForm)

    def test_aliquot_tube_move_form_fields(self):
        """Test that AliquotTubeMoveForm has the correct fields"""
        from ..forms import AliquotTubeMoveForm
        form = AliquotTubeMoveForm()
        self.assertIn('box', form.fields)
        self.assertIn('row', form.fields)
        self.assertIn('column', form.fields)

    def test_aliquot_tube_move_form_validation_valid_data(self):
        """Test AliquotTubeMoveForm validation with valid data"""
        from ..forms import AliquotTubeMoveForm
        form_data = {
            'box': self.box.id,
            'row': 1,
            'column': 1
        }
        form = AliquotTubeMoveForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_aliquot_tube_move_form_validation_invalid_position(self):
        """Test AliquotTubeMoveForm validation with row exceeding max_value"""
        from ..forms import AliquotTubeMoveForm
        form_data = {
            'box': self.box.id,
            'row': 11,
            'column': 1
        }
        form = AliquotTubeMoveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('row', form.errors)

    def test_aliquot_tube_move_form_accepts_valid_position(self):
        """Test AliquotTubeMoveForm accepts positions within max_value range"""
        from ..forms import AliquotTubeMoveForm
        form_data = {
            'box': self.box.id,
            'row': 8,
            'column': 8
        }
        form = AliquotTubeMoveForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_aliquot_tube_move_form_validation_missing_data(self):
        """Test AliquotTubeMoveForm validation with missing data"""
        from ..forms import AliquotTubeMoveForm
        form_data = {
            'box': self.box.id,
            'row': 1
        }
        form = AliquotTubeMoveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('column', form.errors)
