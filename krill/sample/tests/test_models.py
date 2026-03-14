from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError

from ..models.sample import Sample
from ..models.aliquot import (
    Aliquot, AliquotType, AliquotDisposition,
    AliquotLocation,
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
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.assertEqual(aliquot.disposition, self.stored_disposition)
        self.assertEqual(aliquot.disposition.disposition_type, "stored")

    def test_aliquot_disposition_direct(self):
        """Test aliquot disposition is a direct FK"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.assertEqual(aliquot.disposition.disposition_type, "stored")
        aliquot.disposition = self.in_use_disposition
        aliquot.save()
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition.disposition_type, "in_use")

    def test_aliquot_string_representation(self):
        """Test aliquot string representation"""
        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        self.assertIn(self.sample.name, str(aliquot))

    def test_aliquot_store_in_location(self):
        """Test storing an aliquot in a specific location"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.in_use_disposition,
        )
        location = aliquot.store_in_location(box, 5, 5)
        self.assertEqual(location.box, box)
        self.assertEqual(location.row, 5)
        self.assertEqual(location.column, 5)
        # Disposition should be updated to stored
        aliquot.refresh_from_db()
        self.assertEqual(aliquot.disposition.disposition_type, "stored")

    def test_store_in_location_occupied_position(self):
        """Test that store_in_location raises ValidationError for occupied position"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)

        aliquot1 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        aliquot2 = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )

        aliquot1.store_in_location(box, 5, 5)

        with self.assertRaises(ValidationError) as cm:
            aliquot2.store_in_location(box, 5, 5)
        self.assertIn('occupied', str(cm.exception).lower())

    def test_aliquot_location_unique_per_aliquot(self):
        """Test that each aliquot has at most one location"""
        site = Site.objects.create(name="Test Site")
        device = Device.objects.create(name="Test Device", site=site)
        shelf = Shelf.objects.create(name="Test Shelf", device=device)
        rack = Rack.objects.create(name="Test Rack", shelf=shelf)
        box = Box.objects.create(name="Test Box", rack=rack, rows=10, columns=10)

        aliquot = Aliquot.objects.create(
            sample=self.sample,
            aliquot_type=self.aliquot_type,
            disposition=self.stored_disposition,
        )
        AliquotLocation.objects.create(aliquot=aliquot, box=box, row=1, column=1)

        with self.assertRaises(IntegrityError):
            AliquotLocation.objects.create(aliquot=aliquot, box=box, row=2, column=2)
