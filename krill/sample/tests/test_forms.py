from django.test import TestCase
from django.contrib.auth import get_user_model
from django import forms

from ..models.sample import Sample
from ..models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation,
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
        self.assertIn('Unique identifier for', str(form.fields['name'].help_text))
        self.assertIn('origin of the sample', str(form.fields['source'].help_text))
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
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
    def test_aliquot_form_validation_with_valid_data(self):
        """Test aliquot form validation with valid data"""
        form_data = {
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertEqual(aliquot.sample, self.sample)
        self.assertEqual(aliquot.aliquot_type, self.aliquot_type)
        self.assertEqual(aliquot.disposition, self.stored_disposition)

    def test_aliquot_form_with_parent_selection(self):
        """Test aliquot form with parent selection"""
        form_data = {
            'parent': self.parent_aliquot.id,
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertEqual(aliquot.parent, self.parent_aliquot)

    def test_aliquot_form_disposition_selection(self):
        """Test aliquot form disposition selection"""
        form_data = {
            'sample': self.sample.id,
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.in_use_disposition.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertTrue(form.is_valid())
        aliquot = form.save()
        self.assertEqual(aliquot.disposition, self.in_use_disposition)

    def test_aliquot_form_error_handling_missing_required_fields(self):
        """Test aliquot form error handling for missing required fields"""
        # Missing sample (required)
        form_data = {
            'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id,
            'access_level': 'all_members',
        }
        form = AliquotForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('sample', form.errors)

    def test_aliquot_form_widgets_and_help_texts(self):
        """Test aliquot form widgets and help texts"""
        form = AliquotForm()
        self.assertIn('Parent aliquot, if this is a derivative', str(form.fields['parent'].help_text))
        self.assertIn('Sample this aliquot belongs to', str(form.fields['sample'].help_text))
        self.assertIn('Type of aliquot', str(form.fields['aliquot_type'].help_text))
        self.assertIn('Restrict access to specific user tiers', str(form.fields['access_level'].help_text))

    def test_aliquot_form_no_quantity_field(self):
        """Test that AliquotForm does not have a quantity field"""
        form = AliquotForm()
        self.assertNotIn('quantity', form.fields)

    def test_aliquot_form_has_count_field(self):
        """Test that AliquotForm has a count field"""
        form = AliquotForm()
        self.assertIn('count', form.fields)

    def test_aliquot_form_has_disposition_field(self):
        """Test that AliquotForm has a disposition field"""
        form = AliquotForm()
        self.assertIn('disposition', form.fields)


class AliquotLocationFormTest(TestCase):
    """Test cases for the AliquotLocationForm"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
        self.aliquot_type = AliquotType.objects.create(name="Test Type")
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            disposition_type="stored"
        )
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
    def test_aliquot_location_form_validation_with_valid_data(self):
        """Test aliquot location form validation with valid data"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 5,
            'column': 5,
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())
        location = form.save()
        self.assertEqual(location.aliquot, self.aliquot)
        self.assertEqual(location.box, self.box)
        self.assertEqual(location.row, 5)
        self.assertEqual(location.column, 5)

    def test_aliquot_location_form_no_tube_number(self):
        """Test that AliquotLocationForm does not have a tube_number field"""
        form = AliquotLocationForm()
        self.assertNotIn('tube_number', form.fields)

    def test_aliquot_location_form_accepts_any_row(self):
        """Test aliquot location form accepts any integer row"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 15,
            'column': 5,
        }
        form = AliquotLocationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_aliquot_location_form_accepts_any_column(self):
        """Test aliquot location form accepts any integer column"""
        form_data = {
            'aliquot': self.aliquot.id,
            'box': self.box.id,
            'row': 5,
            'column': 15,
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


class AliquotMoveFormTest(TestCase):
    """Test cases for the AliquotMoveForm (replaces AliquotTubeMoveForm)"""

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
        self.stored_disposition = AliquotDisposition.objects.create(
            name="Stored",
            disposition_type="stored"
        )
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
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

    def test_aliquot_move_form_creation(self):
        """Test AliquotMoveForm creation"""
        from ..forms import AliquotMoveForm
        form = AliquotMoveForm()
        self.assertIsInstance(form, AliquotMoveForm)

    def test_aliquot_move_form_fields(self):
        """Test that AliquotMoveForm has the correct fields"""
        from ..forms import AliquotMoveForm
        form = AliquotMoveForm()
        self.assertIn('box', form.fields)
        self.assertIn('row', form.fields)
        self.assertIn('column', form.fields)

    def test_aliquot_move_form_validation_valid_data(self):
        """Test AliquotMoveForm validation with valid data"""
        from ..forms import AliquotMoveForm
        form_data = {
            'box': self.box.id,
            'row': 1,
            'column': 1
        }
        form = AliquotMoveForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_aliquot_move_form_validation_invalid_position(self):
        """Test AliquotMoveForm validation with row exceeding max_value"""
        from ..forms import AliquotMoveForm
        form_data = {
            'box': self.box.id,
            'row': 11,
            'column': 1
        }
        form = AliquotMoveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('row', form.errors)

    def test_aliquot_move_form_accepts_valid_position(self):
        """Test AliquotMoveForm accepts positions within max_value range"""
        from ..forms import AliquotMoveForm
        form_data = {
            'box': self.box.id,
            'row': 8,
            'column': 8
        }
        form = AliquotMoveForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_aliquot_move_form_validation_missing_data(self):
        """Test AliquotMoveForm validation with missing data"""
        from ..forms import AliquotMoveForm
        form_data = {
            'box': self.box.id,
            'row': 1
        }
        form = AliquotMoveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('column', form.errors)
