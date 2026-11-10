from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from sample.models.aliquot import Aliquot, AliquotLocation
from sample.models.sample import Sample
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf


class FixCanesLayoutCommandTest(TestCase):
    def setUp(self):
        self.site = Site.objects.create(name='Main')
        self.sample = Sample.objects.create(name='HeLa', source=Source.objects.create(name='Src'))

    def run_command(self, *args):
        out = StringIO()
        call_command('fix_canes_layout', *args, stdout=out)
        return out.getvalue()

    def old_import_layout(self, name='Dewer'):
        """What the old importer made: a shelf per box letter, every cane under the first."""
        device = Device.objects.create(name=name, site=self.site)
        shelves = [Shelf.objects.create(name=letter, device=device) for letter in 'ABC']
        racks = [Rack.objects.create(name=str(n), shelf=shelves[0]) for n in (1, 2)]
        boxes = [Box.objects.create(name=f'{r.name}_{l}', rack=r, rows=10, columns=10)
                 for r in racks for l in 'AB']
        return device, boxes

    def store(self, box, row, column):
        AliquotLocation.objects.create(aliquot=Aliquot.objects.create(sample=self.sample), box=box, row=row, column=column)

    def test_dry_run_changes_nothing(self):
        device, _ = self.old_import_layout()
        output = self.run_command()
        self.assertIn("rename shelf 'A' to 'Canes', remove 2 empty shelf(s)", output)
        self.assertIn('Dry run', output)
        self.assertEqual(Shelf.objects.filter(device=device).count(), 3)
        self.assertEqual({b.rows for b in Box.objects.all()}, {10})

    def test_yes_repairs_the_old_import_layout(self):
        device, _ = self.old_import_layout()
        self.run_command('--yes')
        self.assertEqual([s.name for s in Shelf.objects.filter(device=device)], ['Canes'])
        self.assertEqual({r.shelf.name for r in Rack.objects.all()}, {'Canes'})
        self.assertEqual(Box.objects.count(), 4)
        self.assertEqual({(b.rows, b.columns) for b in Box.objects.all()}, {(9, 9)})

    def test_box_with_a_tube_beyond_9x9_stays_10x10_and_locations_survive(self):
        _, boxes = self.old_import_layout()
        self.store(boxes[0], 10, 3)
        self.store(boxes[1], 2, 2)
        self.run_command('--yes')
        for box in boxes[:2]:
            box.refresh_from_db()
        self.assertEqual((boxes[0].rows, boxes[0].columns), (10, 10))
        self.assertEqual((boxes[1].rows, boxes[1].columns), (9, 9))
        self.assertEqual(AliquotLocation.objects.count(), 2)

    def test_freezer_with_racks_on_several_shelves_is_left_alone(self):
        device = Device.objects.create(name='Freezer', site=self.site)
        top, bottom = Shelf.objects.create(name='Top', device=device), Shelf.objects.create(name='Bottom', device=device)
        Rack.objects.create(name='R1', shelf=top)
        Rack.objects.create(name='R2', shelf=bottom)
        box = Box.objects.create(name='B', rack=Rack.objects.get(name='R1'), rows=10, columns=10)
        self.assertIn('Nothing to fix', self.run_command('--yes'))
        self.assertEqual(sorted(s.name for s in Shelf.objects.all()), ['Bottom', 'Top'])
        box.refresh_from_db()
        self.assertEqual((box.rows, box.columns), (10, 10))

    def test_rerun_is_a_no_op(self):
        self.old_import_layout()
        self.run_command('--yes')
        self.assertIn('Nothing to fix', self.run_command('--yes'))
        self.assertEqual(Shelf.objects.filter(name='Canes').count(), 1)
