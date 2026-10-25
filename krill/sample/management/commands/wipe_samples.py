from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from person.models import Permission
from sample.models.aliquot import Aliquot, AliquotLocation
from sample.models.sample import Sample
from sample.models.source import Source


def _with_descendants(aliquot_ids):
    """Expand a set of aliquot ids with every child reached via Aliquot.parent."""
    ids = set(aliquot_ids)
    frontier = set(ids)
    while frontier:
        frontier = set(
            Aliquot.objects.filter(parent_id__in=frontier)
            .exclude(id__in=ids)
            .values_list('id', flat=True)
        )
        ids |= frontier
    return ids


def plan_wipe(source_id=None, box_id=None, site_id=None):
    """Work out what a wipe would delete without deleting anything.

    With no filters every sample is wiped (aliquots and locations cascade).
    --source limits the wipe to that source's samples. --box and --site limit
    it to the aliquots stored there; their samples are left in place.
    """
    if box_id is not None or site_id is not None:
        locations = AliquotLocation.objects.all()
        if box_id is not None:
            locations = locations.filter(box_id=box_id)
        if site_id is not None:
            locations = locations.filter(box__rack__shelf__device__site_id=site_id)
        if source_id is not None:
            locations = locations.filter(aliquot__sample__source_id=source_id)
        aliquot_ids = _with_descendants(locations.values_list('aliquot_id', flat=True))
        return {
            'sample_ids': [],
            'aliquot_ids': aliquot_ids,
            'location_count': AliquotLocation.objects.filter(aliquot_id__in=aliquot_ids).count(),
        }

    samples = Sample.objects.all()
    if source_id is not None:
        samples = samples.filter(source_id=source_id)
    sample_ids = list(samples.values_list('id', flat=True))
    aliquot_ids = _with_descendants(
        Aliquot.objects.filter(sample_id__in=sample_ids).values_list('id', flat=True)
    )
    return {
        'sample_ids': sample_ids,
        'aliquot_ids': aliquot_ids,
        'location_count': AliquotLocation.objects.filter(aliquot_id__in=aliquot_ids).count(),
    }


def execute_wipe(plan, include_sources=False):
    """Hard-delete what plan_wipe described. Returns counts of removed rows."""
    sample_ct = ContentType.objects.get_for_model(Sample)
    aliquot_ct = ContentType.objects.get_for_model(Aliquot)
    sample_ids = plan['sample_ids']
    aliquot_ids = plan['aliquot_ids']

    with transaction.atomic():
        # Permission uses a GenericForeignKey, so the database will not cascade.
        permissions = Permission.objects.filter(
            content_type=sample_ct, object_id__in=sample_ids
        ) | Permission.objects.filter(
            content_type=aliquot_ct, object_id__in=aliquot_ids
        )
        permission_count = permissions.count()
        permissions.delete()

        # Aliquot ids must be deleted explicitly when only aliquots are in scope;
        # deleting samples cascades to them otherwise.
        Aliquot.objects.filter(id__in=aliquot_ids).delete()
        Sample.objects.filter(id__in=sample_ids).delete()

        source_count = 0
        if include_sources:
            empty_sources = Source.objects.filter(sample__isnull=True)
            source_count = empty_sources.count()
            empty_sources.delete()

    return {
        'samples': len(sample_ids),
        'aliquots': len(aliquot_ids),
        'locations': plan['location_count'],
        'permissions': permission_count,
        'sources': source_count,
    }


class Command(BaseCommand):
    help = (
        'Hard-delete samples and their aliquots/locations. '
        'Prints what would be deleted and does nothing unless --yes is given. '
        'Take a database backup first.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Actually delete.')
        parser.add_argument('--source', type=int, help='Only samples from this Source id.')
        parser.add_argument('--box', type=int, help='Only aliquots stored in this Box id.')
        parser.add_argument('--site', type=int, help='Only aliquots stored in this Site id.')
        parser.add_argument(
            '--include-sources',
            action='store_true',
            help='Also delete Sources left with no samples.',
        )

    def handle(self, *args, **options):
        if options['source'] is not None and not Source.objects.filter(pk=options['source']).exists():
            raise CommandError(f"No Source with id {options['source']}")

        plan = plan_wipe(options['source'], options['box'], options['site'])
        self.stdout.write(
            f"Would delete {len(plan['sample_ids'])} samples, "
            f"{len(plan['aliquot_ids'])} aliquots, "
            f"{plan['location_count']} locations."
        )

        if not options['yes']:
            self.stdout.write('Dry run. Re-run with --yes to delete.')
            return

        counts = execute_wipe(plan, include_sources=options['include_sources'])
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {counts['samples']} samples, {counts['aliquots']} aliquots, "
            f"{counts['locations']} locations, {counts['permissions']} permissions, "
            f"{counts['sources']} sources."
        ))
