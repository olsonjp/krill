from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError

from sample.models.aliquot import AliquotLocation
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf


class Command(BaseCommand):
    help = (
        'Delete a site, or a single freezer, together with its shelves, racks and boxes. '
        'Prints what would be deleted and does nothing unless --yes is given. '
        'Refuses if any aliquot is still stored in the affected boxes (run wipe_samples first). '
        'Take a database backup first.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--site', help='Name of the site to delete, with every freezer in it.')
        parser.add_argument(
            '--freezer',
            help='Name of one freezer to delete (the site is kept). Add --site if the name is used in several sites.',
        )
        parser.add_argument('--yes', action='store_true', help='Actually delete.')

    def find_scope(self, site_name, freezer_name):
        """Return (site or None, devices queryset) for what the options select."""
        if not site_name and not freezer_name:
            raise CommandError('Give --site NAME to delete a whole site, or --freezer NAME to delete one freezer.')

        site = None
        if site_name:
            sites = list(Site.objects.filter(name=site_name))
            if not sites:
                raise CommandError(f"No site named '{site_name}'.")
            if len(sites) > 1:
                raise CommandError(f"{len(sites)} sites are named '{site_name}'; refusing to guess.")
            site = sites[0]

        if freezer_name:
            devices = Device.objects.filter(name=freezer_name)
            if site:
                devices = devices.filter(site=site)
            count = devices.count()
            if count == 0:
                raise CommandError(f"No freezer named '{freezer_name}'" + (f" in site '{site_name}'." if site else '.'))
            if count > 1:
                raise CommandError(f"{count} freezers are named '{freezer_name}'; add --site to choose one.")
            return None, devices      # a single freezer: the site stays
        return site, Device.objects.filter(site=site)

    def handle(self, *args, **options):
        site, devices = self.find_scope(options['site'], options['freezer'])
        shelves = Shelf.objects.filter(device__in=devices)
        racks = Rack.objects.filter(shelf__in=shelves)
        boxes = Box.objects.filter(rack__in=racks)

        stored = AliquotLocation.objects.filter(box__in=boxes).count()
        if stored:
            raise CommandError(
                f'{stored} aliquot(s) are still stored in these boxes. Remove them first '
                '(e.g. manage.py wipe_samples) so nothing loses its location.'
            )

        counts = (devices.count(), shelves.count(), racks.count(), boxes.count())
        freezer_names = ', '.join(devices.values_list('name', flat=True))
        site_label = f"site '{site.name}', " if site else ''
        self.stdout.write(
            f"Would delete {site_label}{counts[0]} freezer(s) ({freezer_names}), "
            f"{counts[1]} shelves, {counts[2]} racks, {counts[3]} boxes."
        )
        if not options['yes']:
            self.stdout.write('Dry run. Re-run with --yes to delete.')
            return

        try:
            with transaction.atomic():       # children first: the foreign keys are PROTECT
                boxes.delete()
                racks.delete()
                shelves.delete()
                devices.delete()
                if site:
                    site.delete()
        except ProtectedError as error:
            raise CommandError(f'Nothing was deleted: something else still references these rows ({error}).')
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {site_label}{counts[0]} freezer(s), {counts[1]} shelves, {counts[2]} racks, {counts[3]} boxes."
        ))
