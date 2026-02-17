from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError

from ..models.sample import Sample
from ..models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation, AliquotTube
)
from ..models.source import Source
from storage.models.storage import Device, Shelf, Rack, Box
from storage.models.site import Site


class SampleModelTest(TestCase):
    """Test cases for the Sample model"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source for samples"
        )
    def test_sample_creation_with_required_fields(self):
        """Test sample creation with all required fields"""
        sample = Sample.objects.create(
            name="Test Sample 1",
            source=self.source,
            experiment="Test experiment",
            notes="Test notes"
        )
        self.assertEqual(sample.name, "Test Sample 1")
        self.assertEqual(sample.source, self.source)
        self.assertEqual(sample.experiment, "Test experiment")
        self.assertEqual(sample.notes, "Test notes")
        self.assertIsNotNone(sample.id)
    def test_sample_creation_minimal_fields(self):
        """Test sample creation with only required fields"""
        sample = Sample.objects.create(
            name="Test Sample 2",
            source=self.source
        )
        self.assertEqual(sample.name, "Test Sample 2")
        self.assertEqual(sample.source, self.source)
        self.assertIsNone(sample.experiment)
        self.assertIsNone(sample.notes)
    def test_sample_string_representation(self):
        """Test sample string representation"""
        sample = Sample.objects.create(
            name="Test Sample 3",
            source=self.source
        )
        self.assertEqual(str(sample), "Test Sample 3")


class AliquotTypeModelTest(TestCase):
    """Test cases for the AliquotType model"""
    def test_aliquot_type_creation_and_validation(self):
        """Test aliquot type creation with valid data"""
        aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.assertEqual(aliquot_type.name, "Test Type")
        self.assertEqual(aliquot_type.description, "A test aliquot type")
        self.assertIsNotNone(aliquot_type.id)
    def test_aliquot_type_name_uniqueness(self):
        """Test aliquot type name uniqueness constraint"""
        AliquotType.objects.create(
            name="Unique Type",
            description="First type"
        )
        with self.assertRaises(IntegrityError):
            AliquotType.objects.create(
                name="Unique Type",
                description="Second type"
            )
    def test_aliquot_type_string_representation(self):
        """Test aliquot type string representation"""
        aliquot_type = AliquotType.objects.create(
            name="Test Type",
            description="A test aliquot type"
        )
        self.assertEqual(str(aliquot_type), "Test Type")


class AliquotDispositionModelTest(TestCase):
    """Test cases for the AliquotDisposition model"""
    def test_disposition_creation_with_valid_type(self):
        """Test disposition creation with valid disposition type"""
        disposition = AliquotDisposition.objects.create(
            name="Test Stored",
            disposition_type="stored"
        )
        self.assertEqual(disposition.name, "Test Stored")
        self.assertEqual(disposition.disposition_type, "stored")
    def test_disposition_type_choices_validation(self):
        """Test disposition type choices validation"""
        valid_types = ['stored', 'exhausted', 'in_use', 'disposed']
        for disp_type in valid_types:
            disposition = AliquotDisposition.objects.create(
                name=f"Test {disp_type}",
                disposition_type=disp_type
            )
            self.assertEqual(disposition.disposition_type, disp_type)
    def test_disposition_name_uniqueness(self):
        """Test disposition name uniqueness constraint"""
        AliquotDisposition.objects.create(
            name="Unique Disposition",
            disposition_type="stored"
        )
        with self.assertRaises(IntegrityError):
            AliquotDisposition.objects.create(
                name="Unique Disposition",
                disposition_type="exhausted"
            )
    def test_disposition_string_representation(self):
        """Test disposition string representation"""
        disposition = AliquotDisposition.objects.create(
            name="Test Disposition",
            disposition_type="stored"
        )
        self.assertEqual(str(disposition), "Test Disposition")
    def test_disposition_default_type(self):
        """Test disposition default type is 'stored'"""
        disposition = AliquotDisposition.objects.create(
            name="Test Default"
        )
        self.assertEqual(disposition.disposition_type, "stored")


class AliquotModelTest(TestCase):
    """Test cases for the Aliquot model"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(
            name="Test Source",
            description="A test source"
        )
        self.sample = Sample.objects.create(
            name="Test Sample",
            source=self.source
        )
        self.aliquot_type = AliquotType.objects.create(
            name="Test Type"
        )
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
    def test_aliquot_creation_with_required_fields(self):
        """Test aliquot creation with all required fields"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
        self.assertEqual(aliquot.disposition, "exhausted")
        aliquot.create_tubes(auto_store=False)
        if hasattr(aliquot, '_disposition_cache'):
            delattr(aliquot, '_disposition_cache')
        self.assertEqual(aliquot.disposition, "stored")
        self.assertEqual(aliquot.stored_tubes_count, 5)
        self.assertEqual(aliquot.unstored_tubes_count, 0)
    def test_aliquot_disposition_state_management(self):
        """Test aliquot disposition state management"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        if hasattr(aliquot, '_disposition_cache'):
            delattr(aliquot, '_disposition_cache')
        self.assertEqual(aliquot.disposition, "stored")
        tubes = AliquotTube.objects.filter(aliquot=aliquot)
        for tube in tubes:
            aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition, "exhausted")
    def test_aliquot_stored_tubes_count_property(self):
        """Test aliquot stored_tubes_count property"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        self.assertEqual(aliquot.stored_tubes_count, 5)
        tubes = AliquotTube.objects.filter(aliquot=aliquot)[:3]
        for tube in tubes:
            aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
        self.assertEqual(aliquot.stored_tubes_count, 2)
    def test_aliquot_unstored_tubes_count_property(self):
        """Test aliquot unstored_tubes_count property"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        self.assertEqual(aliquot.unstored_tubes_count, 0)
        tubes = AliquotTube.objects.filter(aliquot=aliquot)[:2]
        for tube in tubes:
            aliquot.change_tube_disposition(tube.tube_number, self.in_use_disposition)
        self.assertEqual(aliquot.unstored_tubes_count, 2)
    def test_explicit_tube_creation(self):
        """Test explicit tube creation functionality"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=3,
            aliquot_type=self.aliquot_type
        )
        self.assertEqual(aliquot.tubes.count(), 0)
        self.assertEqual(aliquot.disposition, "exhausted")
        aliquot.create_tubes(auto_store=False)
        if hasattr(aliquot, '_disposition_cache'):
            delattr(aliquot, '_disposition_cache')
        self.assertEqual(aliquot.tubes.count(), 3)
        self.assertEqual(aliquot.disposition, "stored")
        tube_numbers = list(aliquot.tubes.values_list('tube_number', flat=True).order_by('tube_number'))
        self.assertEqual(tube_numbers, [1, 2, 3])
    def test_tube_disposition_change(self):
        """Test changing individual tube dispositions"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=2,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        aliquot.change_tube_disposition(1, self.in_use_disposition)
        tube1 = AliquotTube.objects.get(aliquot=aliquot, tube_number=1)
        self.assertEqual(tube1.disposition.disposition_type, "in_use")
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition, "in_use")
        aliquot.change_tube_disposition(2, self.exhausted_disposition)
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition, "exhausted")
    def test_tube_storage_location(self):
        """Test storing tubes in specific locations"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        aliquot.store_tube_in_location(1, box, 5, 5)
        location = AliquotLocation.objects.get(aliquot=aliquot, tube_number=1)
        self.assertEqual(location.box, box)
        self.assertEqual(location.row, 5)
        self.assertEqual(location.column, 5)
    def test_invalid_tube_number(self):
        """Test error handling for invalid tube numbers"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot.create_tubes(auto_store=False)
        with self.assertRaises(ValidationError):
            aliquot.change_tube_disposition(999, self.in_use_disposition)
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)
        with self.assertRaises(ValidationError):
            aliquot.store_tube_in_location(999, box, 1, 1)

    def test_store_tube_in_location_occupied_position(self):
        """Test that store_tube_in_location raises ValidationError for occupied position"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)

        aliquot1 = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot1.create_tubes(auto_store=False)

        aliquot2 = Aliquot.objects.create(
            sample=self.sample,
            quantity=1,
            aliquot_type=self.aliquot_type
        )
        aliquot2.create_tubes(auto_store=False)

        aliquot1.store_tube_in_location(1, box, 5, 5)

        with self.assertRaises(ValidationError) as cm:
            aliquot2.store_tube_in_location(1, box, 5, 5)
        self.assertIn('occupied', str(cm.exception).lower())


class AliquotTubeModelTest(TestCase):
    """Test cases for the AliquotTube model"""
    def setUp(self):
        """Set up test data"""
        self.source = Source.objects.create(name="Test Source")
        self.sample = Sample.objects.create(name="Test Sample", source=self.source)
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
        self.aliquot = Aliquot.objects.create(
            sample=self.sample,
            quantity=5,
            aliquot_type=self.aliquot_type
        )
    def test_individual_tube_creation_and_tracking(self):
        """Test individual tube creation and tracking"""
        tube = AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )
        self.assertEqual(tube.aliquot, self.aliquot)
        self.assertEqual(tube.tube_number, 1)
        self.assertEqual(tube.disposition, self.stored_disposition)
        self.assertIsNotNone(tube.created_at)
        self.assertIsNotNone(tube.updated_at)
    def test_tube_number_uniqueness_within_aliquot(self):
        """Test tube number uniqueness within aliquot"""
        AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )
        with self.assertRaises(IntegrityError):
            AliquotTube.objects.create(
                aliquot=self.aliquot,
                tube_number=1,
                disposition=self.stored_disposition
            )
    def test_tube_disposition_state_management(self):
        """Test tube disposition state management"""
        tube = AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )
        self.assertEqual(tube.disposition.disposition_type, "stored")
        tube.disposition = self.in_use_disposition
        tube.save()
        self.assertEqual(tube.disposition.disposition_type, "in_use")
    def test_tube_string_representation(self):
        """Test tube string representation"""
        tube = AliquotTube.objects.create(
            aliquot=self.aliquot,
            tube_number=1,
            disposition=self.stored_disposition
        )
        expected_str = f"{self.sample.name} - Tube 1"
        self.assertEqual(str(tube), expected_str)
