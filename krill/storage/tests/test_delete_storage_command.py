from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from sample.models.aliquot import Aliquot, AliquotLocation
from sample.models.sample import Sample
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf


class DeleteStorageCommandTest(TestCase):
    def setUp(self):
        self.old_site = Site.objects.create(name='Old Site')
        self.keep_site = Site.objects.create(name='Keep Site')
        self.old_a = self._freezer(self.old_site, 'Freezer A')
        self.old_b = self._freezer(self.old_site, 'Freezer B')
        self.keep = self._freezer(self.keep_site, 'Freezer A')   # same freezer name, other site

    def _freezer(self, site, name):
        device = Device.objects.create(name=name, site=site)
        shelf = Shelf.objects.create(name='F', device=device)
        rack = Rack.objects.create(name='4', shelf=shelf)
        Box.objects.create(name='4_F', rack=rack, rows=10, columns=10)
        Box.objects.create(name='4_G', rack=rack, rows=10, columns=10)
        return device

    def run_command(self, *args):
        out = StringIO()
        call_command('delete_storage', *args, stdout=out)
        return out.getvalue()

    def test_requires_site_or_freezer(self):
        with self.assertRaises(CommandError):
            self.run_command()

    def test_dry_run_deletes_nothing(self):
        output = self.run_command('--site', 'Old Site')
        self.assertIn("Would delete site 'Old Site', 2 freezer(s)", output)
        self.assertIn('4 boxes', output)
        self.assertIn('Dry run', output)
        self.assertEqual(Site.objects.count(), 2)
        self.assertEqual(Box.objects.count(), 6)

    def test_delete_site_removes_everything_beneath_it_only(self):
        output = self.run_command('--site', 'Old Site', '--yes')
        self.assertIn("Deleted site 'Old Site', 2 freezer(s), 2 shelves, 2 racks, 4 boxes.", output)
        self.assertEqual(list(Site.objects.values_list('name', flat=True)), ['Keep Site'])
        self.assertEqual(Device.objects.count(), 1)
        self.assertEqual(Box.objects.count(), 2)
        self.assertTrue(Device.objects.filter(pk=self.keep.pk).exists())

    def test_delete_single_freezer_keeps_site_and_other_freezers(self):
        self.run_command('--freezer', 'Freezer B', '--yes')
        self.assertEqual(Site.objects.count(), 2)
        self.assertFalse(Device.objects.filter(pk=self.old_b.pk).exists())
        self.assertTrue(Device.objects.filter(pk=self.old_a.pk).exists())
        self.assertEqual(Box.objects.count(), 4)

    def test_ambiguous_freezer_name_needs_site(self):
        with self.assertRaises(CommandError) as ctx:
            self.run_command('--freezer', 'Freezer A', '--yes')
        self.assertIn('add --site', str(ctx.exception))
        self.assertEqual(Device.objects.count(), 3)
        self.run_command('--freezer', 'Freezer A', '--site', 'Old Site', '--yes')
        self.assertEqual(Device.objects.count(), 2)
        self.assertTrue(Device.objects.filter(pk=self.keep.pk).exists())

    def test_unknown_names_are_errors(self):
        with self.assertRaises(CommandError):
            self.run_command('--site', 'Nope')
        with self.assertRaises(CommandError):
            self.run_command('--freezer', 'Nope')

    def test_refuses_while_aliquots_are_stored(self):
        sample = Sample.objects.create(name='S', source=Source.objects.create(name='Src'))
        aliquot = Aliquot.objects.create(sample=sample)
        box = Box.objects.filter(rack__shelf__device=self.old_a).first()
        AliquotLocation.objects.create(aliquot=aliquot, box=box, row=1, column=1)
        with self.assertRaises(CommandError) as ctx:
            self.run_command('--site', 'Old Site', '--yes')
        self.assertIn('1 aliquot(s) are still stored', str(ctx.exception))
        self.assertEqual(Site.objects.count(), 2)
        self.assertEqual(Box.objects.count(), 6)
        # the other site is unaffected by that aliquot
        self.run_command('--site', 'Keep Site', '--yes')
        self.assertEqual(Site.objects.count(), 1)
