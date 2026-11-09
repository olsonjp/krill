from collections import Counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sample.models.aliquot import Aliquot


class Command(BaseCommand):
    help = (
        'Link aliquots to the user who prepared them, based on the initials recorded at import. '
        'Map each set of initials to a username with --map INITIALS=USERNAME (repeatable). '
        'Only aliquots that are not linked yet are touched, and the recorded initials are kept. '
        'Prints what would change and does nothing unless --yes is given. '
        'With no --map it lists the initials that are not linked yet.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--map', action='append', default=[], metavar='INITIALS=USERNAME',
            help='Link aliquots with these initials (any case) to this user, e.g. --map MS=matt.sikora.',
        )
        parser.add_argument('--yes', action='store_true', help='Actually link.')

    def parse_mappings(self, raw_mappings):
        """Return [(initials, user)], validating every entry before anything is changed."""
        User = get_user_model()
        mappings, seen = [], set()
        for raw in raw_mappings:
            initials, separator, username = raw.partition('=')
            initials, username = initials.strip(), username.strip()
            if not separator or not initials or not username:
                raise CommandError(f"Invalid --map '{raw}'. Use INITIALS=USERNAME, e.g. MS=matt.sikora.")
            if initials.casefold() in seen:
                raise CommandError(f"Initials '{initials}' are mapped more than once.")
            seen.add(initials.casefold())
            try:
                user = User.objects.get(**{User.USERNAME_FIELD: username})
            except User.DoesNotExist:
                raise CommandError(f"No user '{username}' (for initials '{initials}'). Nothing was changed.")
            mappings.append((initials, user))
        return mappings

    def display_name(self, user):
        return user.get_full_name() or user.get_username()

    def handle(self, *args, **options):
        mappings = self.parse_mappings(options['map'])
        unlinked = Aliquot.objects.filter(lab_member__isnull=True).exclude(lab_member_initials='')

        plan = [(initials, user, unlinked.filter(lab_member_initials__iexact=initials)) for initials, user in mappings]
        total = 0
        for initials, user, queryset in plan:
            count = queryset.count()
            total += count
            self.stdout.write(f"{initials} -> {self.display_name(user)} ({user.get_username()}): {count} aliquot(s)")

        mapped = {initials.casefold() for initials, _ in mappings}
        left = Counter(
            initials for initials in unlinked.values_list('lab_member_initials', flat=True)
            if initials.casefold() not in mapped
        )
        if left:
            listing = ', '.join(f"{initials} ({count})" for initials, count in left.most_common())
            self.stdout.write(f"Not linked (no mapping): {listing}")
        elif mappings:
            self.stdout.write('Every recorded set of initials is mapped.')
        else:
            self.stdout.write('No unlinked initials.')

        if not mappings:
            return
        if not options['yes']:
            self.stdout.write(f"Dry run: {total} aliquot(s) would be linked. Re-run with --yes to link.")
            return

        with transaction.atomic():
            for _initials, user, queryset in plan:
                queryset.update(lab_member=user)
        self.stdout.write(self.style.SUCCESS(f"Linked {total} aliquot(s)."))
