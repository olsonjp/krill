from django.core.management.base import BaseCommand
from django.db import transaction

from sample.models.aliquot import AliquotLocation
from storage.models.storage import Box, Device, Rack, Shelf

SHELF_NAME = 'Canes'
BOX_SIZE = 9


class Command(BaseCommand):
    help = (
        'Repair freezers laid out by the old importer, which made one shelf per box letter and '
        'hung every cane (rack) under the first of them. In each such freezer the shelf holding '
        "the racks becomes the single 'Canes' shelf, the empty shelves are removed, and 10x10 "
        'boxes that hold no tube beyond 9x9 become 9x9. A freezer whose racks are spread over '
        'several shelves is left alone. No aliquot or location is changed. '
        'Prints the plan and does nothing unless --yes is given. Take a database backup first.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Actually make the changes.')

    def plan_for(self, device):
        """Return (shelf to keep, shelves to remove, boxes to shrink), or None if the freezer is fine."""
        shelves = list(Shelf.objects.filter(device=device).order_by('pk'))
        used = [shelf for shelf in shelves if Rack.objects.filter(shelf=shelf).exists()]
        if len(shelves) < 2 or len(used) != 1:
            return None
        keep = used[0]
        shrink = []
        for box in Box.objects.filter(rack__shelf=keep, rows=10, columns=10):
            beyond = AliquotLocation.objects.filter(box=box)
            if not (beyond.filter(row__gt=BOX_SIZE).exists() or beyond.filter(column__gt=BOX_SIZE).exists()):
                shrink.append(box)
        return keep, [shelf for shelf in shelves if shelf.pk != keep.pk], shrink

    def handle(self, *args, **options):
        plans = [(device, plan) for device in Device.objects.order_by('pk')
                 if (plan := self.plan_for(device))]
        if not plans:
            self.stdout.write('Nothing to fix: no freezer has the old one-shelf-per-box-letter layout.')
            return

        for device, (keep, remove, shrink) in plans:
            self.stdout.write(
                f"{device.name}: rename shelf '{keep.name}' to '{SHELF_NAME}', remove {len(remove)} empty "
                f"shelf(s) ({', '.join(s.name for s in remove)}), resize {len(shrink)} box(es) to {BOX_SIZE}x{BOX_SIZE}."
            )
        if not options['yes']:
            self.stdout.write('Dry run. Re-run with --yes to apply.')
            return

        with transaction.atomic():
            for _device, (keep, remove, shrink) in plans:
                Shelf.objects.filter(pk__in=[s.pk for s in remove]).delete()
                Shelf.objects.filter(pk=keep.pk).update(name=SHELF_NAME)
                Box.objects.filter(pk__in=[b.pk for b in shrink]).update(rows=BOX_SIZE, columns=BOX_SIZE)
        self.stdout.write(self.style.SUCCESS(f'Fixed {len(plans)} freezer(s).'))
