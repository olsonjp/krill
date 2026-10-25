from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from person.models import Permission
from sample.models.aliquot import Aliquot, AliquotLocation
from sample.models.sample import Sample
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf


class WipeSamplesCommandTest(TestCase):
    def setUp(self):
        self.source_a = Source.objects.create(name="Source A")
        self.source_b = Source.objects.create(name="Source B")

        site = Site.objects.create(name="Site")
        device = Device.objects.create(name="Freezer", site=site)
        shelf = Shelf.objects.create(name="Shelf", device=device)
        rack = Rack.objects.create(name="Rack", shelf=shelf)
        self.box1 = Box.objects.create(name="Box 1", rack=rack, rows=10, columns=10)
        self.box2 = Box.objects.create(name="Box 2", rack=rack, rows=10, columns=10)
        self.site = site

        self.sample_a = Sample.objects.create(name="A", source=self.source_a)
        self.sample_b = Sample.objects.create(name="B", source=self.source_b)
        self.aliquot_a = Aliquot.objects.create(sample=self.sample_a)
        self.child_a = Aliquot.objects.create(sample=self.sample_a, parent=self.aliquot_a)
        self.aliquot_b = Aliquot.objects.create(sample=self.sample_b)
        AliquotLocation.objects.create(aliquot=self.aliquot_a, box=self.box1, row=1, column=1)
        AliquotLocation.objects.create(aliquot=self.aliquot_b, box=self.box2, row=1, column=1)

    def run_command(self, *args):
        out = StringIO()
        call_command('wipe_samples', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_deletes_nothing(self):
        output = self.run_command()
        self.assertIn('Would delete 2 samples, 3 aliquots, 2 locations', output)
        self.assertIn('Dry run', output)
        self.assertEqual(Sample.objects.count(), 2)
        self.assertEqual(Aliquot.objects.count(), 3)

    def test_yes_wipes_everything_and_keeps_storage(self):
        self.run_command('--yes')
        self.assertEqual(Sample.objects.count(), 0)
        self.assertEqual(Aliquot.objects.count(), 0)
        self.assertEqual(AliquotLocation.objects.count(), 0)
        self.assertEqual(Source.objects.count(), 2)
        self.assertEqual(Box.objects.count(), 2)

    def test_include_sources_removes_empty_sources(self):
        self.run_command('--yes', '--include-sources')
        self.assertEqual(Source.objects.count(), 0)

    def test_source_filter_scopes_wipe(self):
        self.run_command('--yes', '--source', str(self.source_a.id))
        self.assertFalse(Sample.objects.filter(id=self.sample_a.id).exists())
        self.assertFalse(Aliquot.objects.filter(id=self.child_a.id).exists())
        self.assertTrue(Sample.objects.filter(id=self.sample_b.id).exists())
        self.assertTrue(Aliquot.objects.filter(id=self.aliquot_b.id).exists())

    def test_box_filter_removes_only_aliquots_in_box(self):
        self.run_command('--yes', '--box', str(self.box1.id))
        self.assertFalse(Aliquot.objects.filter(id=self.aliquot_a.id).exists())
        self.assertFalse(Aliquot.objects.filter(id=self.child_a.id).exists())
        self.assertTrue(Aliquot.objects.filter(id=self.aliquot_b.id).exists())
        self.assertEqual(Sample.objects.count(), 2)

    def test_site_filter_matches_every_box_in_site(self):
        self.run_command('--yes', '--site', str(self.site.id))
        self.assertEqual(Aliquot.objects.count(), 0)
        self.assertEqual(Sample.objects.count(), 2)

    def test_orphan_permissions_removed(self):
        user = get_user_model().objects.create_user('u', password='x')
        Permission.objects.create(
            user=user, permission_type='view',
            content_type=ContentType.objects.get_for_model(Sample),
            object_id=self.sample_a.id,
        )
        Permission.objects.create(
            user=user, permission_type='view',
            content_type=ContentType.objects.get_for_model(Aliquot),
            object_id=self.aliquot_a.id,
        )
        keep = Permission.objects.create(
            user=user, permission_type='view',
            content_type=ContentType.objects.get_for_model(Sample),
            object_id=self.sample_b.id,
        )
        self.run_command('--yes', '--source', str(self.source_a.id))
        self.assertEqual(list(Permission.objects.all()), [keep])

    def test_unknown_source_errors(self):
        with self.assertRaises(CommandError):
            self.run_command('--source', '99999')
