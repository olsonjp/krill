import datetime
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.urls import reverse

from .. import list_filters as lf
from ..models.aliquot import Aliquot, AliquotDisposition, AliquotType
from ..models.sample import Sample
from .test_views import SampleViewTest

User = get_user_model()


class FilterFixture(SampleViewTest):
    def setUp(self):
        super().setUp()
        Aliquot.objects.all().delete()
        self.client.force_login(self.user)
        self.url = reverse('sample:sample_list')
        self.hela = Sample.objects.create(name='HeLa S3', source=self.source, experiment='Exp 12', notes='thawed twice')
        self.jurkat = Sample.objects.create(name='Jurkat', source=self.source)
        self.in_use = AliquotDisposition.objects.get_or_create(name='In Use', defaults={'disposition_type': 'in_use'})[0]

    def make(self, sample=None, **kwargs):
        kwargs.setdefault('aliquot_type', self.aliquot_type)
        kwargs.setdefault('disposition', self.stored_disposition)
        return Aliquot.objects.create(sample=sample or self.hela, **kwargs)

    def names(self, response):
        return [a.pk for a in response.context['items']]

    def list(self, **params):
        return self.client.get(self.url, {'type': 'aliquot', **params})

    def ids(self, **params):
        return sorted(self.names(self.list(**params)))


class ParsingHelpersTest(FilterFixture):
    def test_split_words_keeps_quoted_phrases_together(self):
        self.assertEqual(lf.split_words('hela p8'), ['hela', 'p8'])
        self.assertEqual(lf.split_words('hela "cell line" p8'), ['hela', 'cell line', 'p8'])
        self.assertEqual(lf.split_words('  '), [])
        self.assertEqual(lf.split_words('"open quote'), ['"open', 'quote'])

    def test_parse_date(self):
        self.assertEqual(lf.parse_date('2025-03-01'), datetime.date(2025, 3, 1))
        for bad in ('', 'x', '2025-13-01', None):
            self.assertIsNone(lf.parse_date(bad))

    def test_url_without_drops_the_parameter_and_the_page_but_keeps_the_rest(self):
        request = SimpleNamespace(GET=QueryDict('type=aliquot&f_sample=hela&sort=passage&order=desc&page=3'), path='/samples/list/')
        self.assertEqual(
            lf.FilterSpec.url_without(request, 'f_sample'),
            '?type=aliquot&sort=passage&order=desc')
        only = SimpleNamespace(GET=QueryDict('page=2'), path='/samples/list/')
        self.assertEqual(lf.FilterSpec.url_without(only), '/samples/list/')


class SampleFieldTest(FilterFixture):
    def test_contains_ignoring_case_and_every_word_must_appear(self):
        a, b = self.make(self.hela), self.make(self.jurkat)
        self.assertEqual(self.ids(f_sample='hela'), [a.pk])
        self.assertEqual(self.ids(f_sample='S3 he'), [a.pk])        # both words, any order
        self.assertEqual(self.ids(f_sample='jurk'), [b.pk])
        self.assertEqual(self.ids(f_sample='zzz'), [])

    def test_a_quoted_phrase_is_kept_together(self):
        a = self.make(self.hela)
        self.assertEqual(self.ids(f_sample='"HeLa S3"'), [a.pk])
        self.assertEqual(self.ids(f_sample='"S3 HeLa"'), [])


class PassageFieldTest(FilterFixture):
    def setUp(self):
        super().setUp()
        self.p8 = self.make(passage='p8')
        self.p80 = self.make(passage='p80')
        self.p8_3 = self.make(passage='P8+3')
        self.p9 = self.make(passage='p9')
        self.none = self.make(passage='')

    def test_exact_ignoring_case_so_p8_does_not_match_p80(self):
        self.assertEqual(self.ids(f_passage='p8'), [self.p8.pk])
        self.assertEqual(self.ids(f_passage='P8'), [self.p8.pk])

    def test_a_trailing_star_matches_the_start(self):
        self.assertEqual(self.ids(f_passage='P8*'), sorted([self.p8.pk, self.p80.pk, self.p8_3.pk]))
        self.assertEqual(self.ids(f_passage='p9*'), [self.p9.pk])

    def test_surrounding_spaces_are_ignored(self):
        self.assertEqual(self.ids(f_passage='  p8  '), [self.p8.pk])

    def test_a_lone_star_or_blank_is_not_a_filter(self):
        everything = sorted(a.pk for a in Aliquot.objects.all())
        self.assertEqual(self.ids(f_passage='*'), everything)
        self.assertEqual(self.ids(f_passage=' '), everything)
        self.assertEqual(self.list(f_passage='*').context['filter_bar'].chips, [])

    def test_the_search_everything_box_is_unchanged_for_loose_matching(self):
        self.assertEqual(self.ids(q='p8'), sorted([self.p8.pk, self.p80.pk, self.p8_3.pk]))


class OtherFieldsTest(FilterFixture):
    def test_lab_member_by_initials_name_and_username(self):
        ada = User.objects.create_user(username='alove', first_name='Ada', last_name='Lovelace', password='x')
        by_user = self.make(lab_member=ada)
        by_initials = self.make(lab_member_initials='XYZ')
        self.make()
        self.assertEqual(self.ids(f_member='lovelace'), [by_user.pk])
        self.assertEqual(self.ids(f_member='ada love'), [by_user.pk])     # first and last name together
        self.assertEqual(self.ids(f_member='alove'), [by_user.pk])
        self.assertEqual(self.ids(f_member='xyz'), [by_initials.pk])

    def test_location_matches_freezer_or_box(self):
        placed, unplaced = self.make(), self.make()
        placed.store_in_location(self.box, 1, 1)
        self.assertEqual(self.ids(f_location='test device'), [placed.pk])
        self.assertEqual(self.ids(f_location='box'), [placed.pk])
        self.assertEqual(self.ids(f_location='nowhere'), [])

    def test_aliquot_number_is_exact(self):
        target = self.make()
        self.make()
        self.assertEqual(self.ids(f_number=str(target.pk)), [target.pk])
        self.assertEqual(self.ids(f_number=f'#{target.pk}'), [target.pk])
        self.assertEqual(self.ids(f_number=str(target.pk) + '0'), [])
        self.assertEqual(self.ids(f_number='abc'), [])

    def test_disposition_and_type_selects_still_filter(self):
        stored = self.make()
        in_use = self.make(disposition=self.in_use)
        other_type = AliquotType.objects.create(name='Pellet')
        pellet = self.make(aliquot_type=other_type)
        self.assertEqual(self.ids(disposition='in_use'), [in_use.pk])
        self.assertEqual(self.ids(aliquot_type=str(other_type.pk)), [pellet.pk])
        self.assertEqual(self.ids(disposition='nonsense'), sorted([stored.pk, in_use.pk, pellet.pk]))
        self.assertEqual(self.ids(aliquot_type='abc'), sorted([stored.pk, in_use.pk, pellet.pk]))


class DateFilterTest(FilterFixture):
    def setUp(self):
        super().setUp()
        d = datetime.date
        self.early = self.make(sample_date=d(2025, 1, 10))
        self.mid = self.make(sample_date=d(2025, 3, 1))
        self.late = self.make(sample_date=d(2025, 6, 30))
        self.undated = self.make(sample_date=None)

    def test_from_only_is_on_or_after(self):
        self.assertEqual(self.ids(f_date_from='2025-03-01'), sorted([self.mid.pk, self.late.pk]))

    def test_to_only_is_on_or_before(self):
        self.assertEqual(self.ids(f_date_to='2025-03-01'), sorted([self.early.pk, self.mid.pk]))

    def test_the_same_date_twice_means_that_day(self):
        self.assertEqual(self.ids(f_date_from='2025-03-01', f_date_to='2025-03-01'), [self.mid.pk])

    def test_a_range(self):
        self.assertEqual(self.ids(f_date_from='2025-02-01', f_date_to='2025-04-01'), [self.mid.pk])

    def test_a_date_that_cannot_be_read_is_ignored(self):
        response = self.list(f_date_from='not-a-date')
        self.assertEqual(len(response.context['items']), 4)
        self.assertEqual(response.context['filter_bar'].chips, [])

    def test_undated_aliquots_are_never_in_a_range_and_the_page_says_so(self):
        response = self.list(f_date_from='2000-01-01')
        self.assertNotIn(self.undated.pk, self.names(response))
        self.assertEqual(response.context['no_date_excluded'], 1)
        self.assertContains(response, '1 aliquot with no sample date is excluded')

    def test_the_note_counts_only_what_the_other_filters_would_have_shown(self):
        self.make(sample=self.jurkat, sample_date=None)
        response = self.list(f_date_from='2000-01-01', f_sample='hela')
        self.assertEqual(response.context['no_date_excluded'], 1)
        self.assertContains(self.list(f_date_from='2000-01-01'), '2 aliquots with no sample date are excluded')

    def test_no_note_without_a_date_filter_or_with_nothing_excluded(self):
        self.assertIsNone(self.list().context['no_date_excluded'])
        self.undated.delete()
        self.assertNotRegex(self.list(f_date_from='2000-01-01').content.decode(),
                            r'with no sample date (is|are) excluded')


class CombiningTest(FilterFixture):
    def test_every_filled_field_must_match(self):
        hit = self.make(self.hela, passage='p8')
        self.make(self.hela, passage='p9')
        self.make(self.jurkat, passage='p8')
        self.assertEqual(self.ids(f_sample='hela', f_passage='p8'), [hit.pk])

    def test_fields_combine_with_search_pills_and_disposition(self):
        hit = self.make(self.hela, passage='p8')
        self.make(self.hela, passage='p8', disposition=self.in_use)
        self.assertEqual(self.ids(f_sample='hela', f_passage='p8', hide_finished='1', disposition='stored', q='hela'), [hit.pk])

    def test_fields_survive_sorting_and_paging_parameters(self):
        for i in range(3):
            self.make(self.hela, passage=f'p{i}')
        response = self.list(f_sample='hela', sort='passage', order='desc', page_size='20')
        self.assertEqual([a.passage for a in response.context['items']], ['p2', 'p1', 'p0'])


class SearchEverythingTest(FilterFixture):
    def test_every_word_must_match_something(self):
        hit = self.make(self.hela, passage='p8')
        self.make(self.hela, passage='p9')
        self.make(self.jurkat, passage='p8')
        self.assertEqual(self.ids(q='hela p8'), [hit.pk])

    def test_words_can_match_different_fields(self):
        ada = User.objects.create_user(username='ada', first_name='Ada', password='x')
        hit = self.make(self.hela, lab_member=ada)
        self.make(self.hela)
        self.assertEqual(self.ids(q='hela ada'), [hit.pk])

    def test_a_quoted_phrase_keeps_the_old_single_phrase_behaviour(self):
        a = self.make(self.hela)
        self.assertEqual(self.ids(q='"hela s3"'), [a.pk])
        self.assertEqual(self.ids(q='"s3 hela"'), [])

    def test_numbers_still_match_the_aliquot_number(self):
        target = self.make()
        self.assertEqual(self.ids(q=f'#{target.pk}')[0], target.pk)

    def test_other_lists_split_words_too(self):
        from ..models.source import Source
        Source.objects.create(name='Big Lab West')
        Source.objects.create(name='Big Lab East')
        response = self.client.get(self.url, {'type': 'source', 'q': 'big west'})
        self.assertEqual([s.name for s in response.context['items']], ['Big Lab West'])


class ChipsTest(FilterFixture):
    def chips(self, **params):
        return {c.text: c.remove_url for c in self.list(**params).context['filter_bar'].chips}

    def test_one_chip_per_field_with_its_rule(self):
        chips = self.chips(f_sample='HeLa', f_passage='P8', f_member='ada', f_location='box', f_number='12',
                           f_date_from='2025-03-01', f_date_to='2025-04-01')
        self.assertEqual(set(chips), {
            'Sample contains HeLa', 'Passage is P8', 'Lab member contains ada', 'Location contains box',
            'Aliquot number is 12', 'Date from 2025-03-01', 'Date to 2025-04-01'})

    def test_prefix_passage_chip(self):
        self.assertIn('Passage starts with P8', self.chips(f_passage='P8*'))

    def test_select_chips_use_the_label_and_name(self):
        pellet = AliquotType.objects.create(name='Pellet')
        chips = self.chips(disposition='in_use', aliquot_type=str(pellet.pk))
        self.assertEqual(set(chips), {'Disposition: In Use', 'Type: Pellet'})

    def test_search_and_sample_filter_chips_come_first(self):
        chips = list(self.chips(q='hela', sample=str(self.hela.pk), f_passage='p8'))
        self.assertEqual(chips, ['"hela"', 'Sample: HeLa S3', 'Passage is p8'])

    def test_each_chip_removes_only_its_own_parameter_and_keeps_the_sort_and_resets_the_page(self):
        chips = self.chips(f_sample='hela', f_passage='p8', sort='passage', order='desc', page='1')
        url = chips['Sample contains hela']
        self.assertIn('f_passage=p8', url)
        self.assertIn('sort=passage', url)
        self.assertIn('order=desc', url)
        self.assertNotIn('f_sample', url)
        self.assertNotIn('page=', url)

    def test_chips_are_links_with_labels_for_screen_readers(self):
        self.make(self.hela)
        response = self.list(f_sample='hela')
        self.assertContains(response, 'aria-label="Remove filter: Sample contains hela"')

    def test_clear_all_only_with_two_or_more_chips(self):
        self.assertFalse(self.list(f_sample='hela').context['filter_bar'].show_clear_all)
        self.assertNotContains(self.list(f_sample='hela'), 'Clear all')
        response = self.list(f_sample='hela', f_passage='p8')
        self.assertTrue(response.context['filter_bar'].show_clear_all)
        self.assertContains(response, 'Clear all')

    def test_clear_all_resets_filters_search_and_pills_but_keeps_sort_and_list_type(self):
        response = self.list(f_sample='hela', f_passage='p8', q='x', hide_finished='1', checked_out_by='me',
                             disposition='stored', sort='passage', order='desc', page_size='20', page='1')
        url = response.context['filter_bar'].clear_all_url
        for gone in ('f_sample', 'f_passage', 'q=', 'hide_finished', 'checked_out_by', 'disposition', 'page='):
            self.assertNotIn(gone, url)
        for kept in ('type=aliquot', 'sort=passage', 'order=desc', 'page_size=20'):
            self.assertIn(kept, url)


class MorePanelTest(FilterFixture):
    def test_inline_fields_and_hints_and_placeholders(self):
        response = self.list()
        self.assertContains(response, 'name="f_sample"')
        # The placeholder is just the name; the rule is a tooltip and is repeated in the More panel
        self.assertContains(response, 'placeholder="Passage"')
        self.assertNotContains(response, 'placeholder="Passage (')
        rule = 'Matches exactly, ignoring case: P8 finds P8 and p8, not P80. End with * to match the start, for example P8*.'
        self.assertContains(response, f'title="{rule}"')
        self.assertContains(response, f'<p><strong>Passage:</strong> {rule}</p>')
        self.assertContains(response, '<small class="filter-hint">On or after. Aliquots with no sample date are left out.</small>')

    def test_disposition_and_type_moved_into_the_panel(self):
        html = self.list().content.decode()
        start = html.index('id="filter-more-panel"')
        panel = html[start:html.index('</form>', start)]
        for name in ('f_member', 'f_date_from', 'f_date_to', 'f_location', 'f_number', 'disposition', 'aliquot_type'):
            with self.subTest(field=name):
                self.assertIn(f'name="{name}"', panel)
        row = html[html.index('class="toolbar-row"'):html.index('id="filter-more-panel"')]
        self.assertNotIn('name="disposition"', row)

    def test_the_panel_is_closed_until_one_of_its_fields_is_used(self):
        self.assertNotRegex(self.list().content.decode(), r'<details class="filter-more"\s+open')
        self.assertRegex(self.list(f_location='x').content.decode(), r'<details class="filter-more"\s+open')
        self.assertRegex(self.list(disposition='stored').content.decode(), r'<details class="filter-more"\s+open')

    def test_inline_fields_alone_do_not_open_it_and_the_count_badge_shows(self):
        self.assertNotRegex(self.list(f_sample='x').content.decode(), r'<details class="filter-more"\s+open')
        response = self.list(f_location='x', f_number='1')
        self.assertEqual(response.context['filter_bar'].more_active, 2)
        self.assertContains(response, 'class="filter-more-count">2<')

    def test_the_form_keeps_the_pills_when_searching(self):
        html = self.list(hide_finished='1', f_passage='p8').content.decode()
        self.assertIn('<input type="hidden" name="hide_finished" value="1">', html)
        self.assertIn('value="p8"', html)

    def test_new_aliquot_button_keeps_a_label_for_screen_readers(self):
        self.assertContains(self.list(), 'aria-label="New Aliquot"')


class ToolbarLayoutTest(FilterFixture):
    """The Aliquots toolbar is one row: search, Sample, Passage, More, Search, New Aliquot."""

    def row(self):
        html = self.list().content.decode()
        return html[html.index('class="toolbar-row"'):html.index('id="filter-more-panel"')]

    def test_controls_are_on_one_row_in_order_with_new_aliquot_last(self):
        row = self.row()
        order = ['name="q"', 'name="f_sample"', 'name="f_passage"', 'class="filter-more"',
                 'class="toolbar-btn-search"', 'toolbar-new']
        positions = [row.index(token) for token in order]
        self.assertEqual(positions, sorted(positions))

    def test_more_is_a_summary_in_the_row_that_controls_the_panel_below(self):
        row = self.row()
        self.assertIn('<summary aria-controls="filter-more-panel">More filters</summary>', row)
        html = self.list().content.decode()
        self.assertIn('id="filter-more-panel"', html)
        self.assertLess(html.index('class="filter-more"'), html.index('id="filter-more-panel"'))

    def test_more_shows_how_many_of_its_fields_are_active(self):
        self.assertIn('More filters<span class="filter-more-count">2</span>',
                      self.list(f_location='x', f_number='1').content.decode())

    def test_no_template_comment_text_leaks_into_the_page(self):
        for params in ({}, {'f_sample': 'x', 'f_passage': 'y'}):
            html = self.list(**params).content.decode()
            for leaked in ('{#', '#}', 'variant:', 'FilterBar', '{% comment', 'endcomment'):
                with self.subTest(params=params, leaked=leaked):
                    self.assertNotIn(leaked, html)
        samples = self.client.get(self.url).content.decode()
        for leaked in ('{#', '#}', 'variant:', 'FilterBar'):
            self.assertNotIn(leaked, samples)

    def test_the_page_header_is_one_description_line(self):
        html = self.list().content.decode()
        header = html[html.index('class="list-header"'):html.index('<!-- Filter toolbar')]
        self.assertEqual(header.count('<p'), 1)
        self.assertIn('An aliquot is one portion of a sample.', header)
        self.assertNotIn('Browse and manage', header)

    def test_lists_without_a_hint_keep_a_single_browse_line(self):
        html = self.client.get(self.url, {'type': 'source'}).content.decode()
        header = html[html.index('class="list-header"'):html.index('<!-- Filter toolbar')]
        self.assertEqual(header.count('<p'), 1)
        self.assertIn('Browse and manage sources.', header)

    def test_every_filter_template_uses_block_comments(self):
        import re
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / 'templates' / 'sample'
        for name in ('_filter_fields.html', '_filter_chips.html'):
            with self.subTest(template=name):
                text = (root / name).read_text()
                for comment in re.findall(r'\{#.*?#\}', text, flags=re.S):
                    self.assertNotIn('\n', comment, 'multi-line {# #} comments render as text; use {% comment %}')


class EmptyAndHeadingTest(FilterFixture):
    def test_nothing_matching_lists_each_filter_with_a_remove_link(self):
        self.make(self.hela, passage='p8')
        response = self.list(f_sample='jurkat', f_passage='p8')
        self.assertContains(response, 'No aliquots match all of these filters.')
        self.assertContains(response, 'Sample contains jurkat')
        self.assertContains(response, 'Passage is p8')
        html = response.content.decode()
        block = html[html.index('no-results-filters'):]
        self.assertEqual(block.count('>remove</a>'), 2)

    def test_the_repeated_heading_is_gone(self):
        html = self.list().content.decode()
        self.assertEqual(html.count('<h2>Aliquots</h2>'), 0)
        self.assertEqual(html.count('<h1>Aliquots</h1>'), 1)

    def test_singular_count_text_survives(self):
        self.make()
        self.assertContains(self.list(), '1 aliquot found')

    def test_existing_context_keys_remain(self):
        context = self.list(disposition='stored').context
        self.assertEqual(context['disposition_filter'], 'stored')
        self.assertIn('disposition_choices', context)
        self.assertIn('aliquot_types', context)


class SamplesListFiltersTest(FilterFixture):
    def sample_list(self, **params):
        return self.client.get(self.url, params)

    def sample_names(self, **params):
        return [s.name for s in self.sample_list(**params).context['items']]

    def test_source_experiment_and_notes_contain(self):
        from ..models.source import Source
        other = Source.objects.create(name='Other Lab')
        Sample.objects.filter(pk=self.jurkat.pk).update(source=other)
        self.assertEqual(self.sample_names(f_source='other'), ['Jurkat'])
        self.assertEqual(self.sample_names(f_experiment='exp 1'), ['HeLa S3'])
        self.assertEqual(self.sample_names(f_notes='thawed'), ['HeLa S3'])

    def test_fields_combine_and_work_with_search_and_the_low_count_pill(self):
        self.make(self.hela)
        self.assertEqual(self.sample_names(f_notes='thawed', q='hela'), ['HeLa S3'])
        self.assertEqual(self.sample_names(f_notes='thawed', q='jurkat'), [])
        self.assertEqual(self.sample_names(f_notes='thawed', low_count='1'), ['HeLa S3'])

    def test_search_splits_words_for_samples(self):
        self.assertEqual(self.sample_names(q='s3 hela'), ['HeLa S3'])
        self.assertEqual(self.sample_names(q='"S3 hela"'), [])

    def test_the_three_fields_are_inline_in_the_search_card_and_chips_appear(self):
        response = self.sample_list(f_source='lab', f_notes='thawed')
        for name in ('f_source', 'f_experiment', 'f_notes'):
            self.assertContains(response, f'name="{name}"')
        chips = [c.text for c in response.context['filter_bar'].chips]
        self.assertEqual(chips, ['Source contains lab', 'Notes contain thawed'])
        self.assertContains(response, 'Clear all')

    def test_no_more_panel_for_a_list_with_three_fields(self):
        self.assertNotContains(self.sample_list(), 'class="filter-more"')

    def test_an_empty_result_names_the_filters(self):
        response = self.sample_list(f_notes='nothing like this')
        self.assertContains(response, 'No samples match all of these filters.')

    def test_the_stored_count_pill_and_columns_are_unchanged(self):
        response = self.sample_list()
        self.assertContains(response, 'Low count &middot;')
        self.assertContains(response, '<th data-sort="stored"')
