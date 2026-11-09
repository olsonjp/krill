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


class AliquotProvenanceFieldsTest(TestCase):
    """Passage, sample date and lab member on Aliquot."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.User = get_user_model()
        source = Source.objects.create(name="Src")
        self.sample = Sample.objects.create(name="HeLa", source=source)
        self.disposition = AliquotDisposition.objects.create(name="Stored", disposition_type="stored")

    def _aliquot(self, **kwargs):
        return Aliquot.objects.create(sample=self.sample, disposition=self.disposition, **kwargs)

    def test_fields_are_optional(self):
        aliquot = self._aliquot()
        self.assertEqual(aliquot.passage, '')
        self.assertIsNone(aliquot.sample_date)
        self.assertIsNone(aliquot.lab_member)
        self.assertEqual(aliquot.lab_member_display, '')

    def test_lab_member_display_falls_back_to_initials(self):
        self.assertEqual(self._aliquot(lab_member_initials='JS').lab_member_display, 'JS')

    def test_lab_member_display_prefers_linked_user(self):
        user = self.User.objects.create_user(username='jsmith', password='x', first_name='Jo', last_name='Smith')
        aliquot = self._aliquot(lab_member=user, lab_member_initials='JS')
        self.assertEqual(aliquot.lab_member_display, 'Jo Smith')

    def test_lab_member_display_uses_username_without_a_name(self):
        user = self.User.objects.create_user(username='jsmith', password='x')
        self.assertEqual(self._aliquot(lab_member=user).lab_member_display, 'jsmith')

    def test_deleting_user_keeps_aliquot_and_initials(self):
        user = self.User.objects.create_user(username='gone', password='x')
        aliquot = self._aliquot(lab_member=user, lab_member_initials='GO')
        user.delete()
        aliquot.refresh_from_db()
        self.assertIsNone(aliquot.lab_member)
        self.assertEqual(aliquot.lab_member_display, 'GO')

    def test_aliquot_form_saves_new_fields(self):
        from ..forms import AliquotForm
        form = AliquotForm(data={
            'sample': self.sample.pk,
            'disposition': self.disposition.pk,
            'access_level': 'all_members',
            'passage': 'p8',
            'sample_date': '2021-07-01',
            'lab_member_initials': 'MS',
        })
        self.assertTrue(form.is_valid(), form.errors)
        aliquot = form.save()
        self.assertEqual((aliquot.passage, str(aliquot.sample_date), aliquot.lab_member_initials), ('p8', '2021-07-01', 'MS'))

    def test_aliquot_detail_page_shows_and_edits_new_fields(self):
        from django.urls import reverse
        admin = self.User.objects.create_superuser(username='root', password='x', email='r@example.com')
        self.client.force_login(admin)
        aliquot = self._aliquot(passage='p8', lab_member_initials='MS')
        aliquot.sample_date = timezone.now().date().replace(year=2021, month=7, day=1)
        aliquot.save()
        url = reverse('sample:aliquot_detail', kwargs={'pk': aliquot.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('p8', body)
        self.assertIn('MS', body)
        self.assertIn('Jul 01, 2021', body)
        # edit through the form
        response = self.client.post(url, {
            'action': 'edit', 'sample': self.sample.pk, 'disposition': self.disposition.pk,
            'access_level': 'all_members', 'passage': 'p9', 'sample_date': '2022-01-05',
            'lab_member_initials': 'JS', 'lab_member': admin.pk,
        })
        self.assertEqual(response.status_code, 302)
        aliquot.refresh_from_db()
        self.assertEqual((aliquot.passage, str(aliquot.sample_date), aliquot.lab_member_id), ('p9', '2022-01-05', admin.pk))
