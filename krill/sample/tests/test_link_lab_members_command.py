from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from sample.models.aliquot import Aliquot
from sample.models.sample import Sample
from sample.models.source import Source


class LinkLabMembersCommandTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.matt = User.objects.create_user(username='matt.sikora', password='x', first_name='Matt', last_name='Sikora')
        self.joe = User.objects.create_user(username='joe.sottnik', password='x', first_name='Joe', last_name='Sottnik')
        sample = Sample.objects.create(name='HeLa', source=Source.objects.create(name='Src'))
        self.ms1 = Aliquot.objects.create(sample=sample, lab_member_initials='MS')
        self.ms2 = Aliquot.objects.create(sample=sample, lab_member_initials='ms')       # other case
        self.js = Aliquot.objects.create(sample=sample, lab_member_initials='JS')
        self.tl = Aliquot.objects.create(sample=sample, lab_member_initials='TL')        # no mapping
        self.tl2 = Aliquot.objects.create(sample=sample, lab_member_initials='TL')
        self.blank = Aliquot.objects.create(sample=sample)                               # no initials at all
        self.already = Aliquot.objects.create(sample=sample, lab_member_initials='MS', lab_member=self.joe)

    def run_command(self, *args):
        out = StringIO()
        call_command('link_lab_members', *args, stdout=out)
        return out.getvalue()

    def linked(self, aliquot):
        aliquot.refresh_from_db()
        return aliquot.lab_member

    def test_without_map_lists_unlinked_initials(self):
        output = self.run_command()
        self.assertIn('Not linked (no mapping)', output)
        self.assertIn('TL (2)', output)
        self.assertIn('MS (1)', output)          # only the aliquot that is not linked yet
        self.assertIsNone(self.linked(self.ms1))

    def test_dry_run_changes_nothing(self):
        output = self.run_command('--map', 'MS=matt.sikora', '--map', 'JS=joe.sottnik')
        self.assertIn('MS -> Matt Sikora (matt.sikora): 2 aliquot(s)', output)
        self.assertIn('JS -> Joe Sottnik (joe.sottnik): 1 aliquot(s)', output)
        self.assertIn('Dry run: 3 aliquot(s) would be linked', output)
        self.assertIsNone(self.linked(self.ms1))
        self.assertIsNone(self.linked(self.js))

    def test_yes_links_matching_initials_in_any_case(self):
        output = self.run_command('--map', 'MS=matt.sikora', '--map', 'JS=joe.sottnik', '--yes')
        self.assertIn('Linked 3 aliquot(s).', output)
        self.assertEqual(self.linked(self.ms1), self.matt)
        self.assertEqual(self.linked(self.ms2), self.matt)
        self.assertEqual(self.linked(self.js), self.joe)

    def test_leaves_unmapped_blank_and_already_linked_aliquots_alone(self):
        self.run_command('--map', 'MS=matt.sikora', '--yes')
        self.assertIsNone(self.linked(self.tl))
        self.assertIsNone(self.linked(self.blank))
        self.assertEqual(self.linked(self.already), self.joe)      # not re-pointed to Matt

    def test_initials_are_kept_and_display_uses_the_user(self):
        self.run_command('--map', 'MS=matt.sikora', '--yes')
        self.ms1.refresh_from_db()
        self.assertEqual(self.ms1.lab_member_initials, 'MS')
        self.assertEqual(self.ms1.lab_member_display, 'Matt Sikora')
        self.assertEqual(self.tl.lab_member_display, 'TL')          # falls back to initials

    def test_rerun_is_a_no_op(self):
        self.run_command('--map', 'MS=matt.sikora', '--yes')
        output = self.run_command('--map', 'MS=matt.sikora', '--yes')
        self.assertIn('MS -> Matt Sikora (matt.sikora): 0 aliquot(s)', output)
        self.assertIn('Linked 0 aliquot(s).', output)

    def test_unknown_user_changes_nothing(self):
        with self.assertRaises(CommandError) as ctx:
            self.run_command('--map', 'MS=matt.sikora', '--map', 'JS=nobody', '--yes')
        self.assertIn("No user 'nobody'", str(ctx.exception))
        self.assertIsNone(self.linked(self.ms1))      # the valid mapping was not applied either

    def test_bad_or_duplicate_mappings_are_errors(self):
        for bad in ('MS', 'MS=', '=matt.sikora'):
            with self.assertRaises(CommandError):
                self.run_command('--map', bad)
        with self.assertRaises(CommandError) as ctx:
            self.run_command('--map', 'MS=matt.sikora', '--map', 'ms=joe.sottnik')
        self.assertIn('more than once', str(ctx.exception))
