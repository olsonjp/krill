import re

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.urls import reverse
from django.utils import timezone

from ..models.aliquot import Aliquot, AliquotDisposition
from .test_views import SampleViewTest

User = get_user_model()


class ResultsBarTest(SampleViewTest):
    """The pills live in the bar directly above the table, with the count and view toggle at the right."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.url = reverse('sample:sample_list')
        self.in_use = AliquotDisposition.objects.get_or_create(name='In Use', defaults={'disposition_type': 'in_use'})[0]

    def html(self, **params):
        return self.client.get(self.url, {'type': 'aliquot', **params}).content.decode()

    @staticmethod
    def bar_of(html):
        """The results bar: from its id to the table, or to the empty-state block when nothing matches."""
        start = html.index('id="results-bar"')
        ends = [html.index(marker, start) for marker in ('<!-- Table view -->', 'class="no-results"') if marker in html[start:]]
        return html[start:min(ends)]

    def bar(self, **params):
        return self.bar_of(self.html(**params))

    def checked_out(self, n=2):
        for _ in range(n):
            Aliquot.objects.create(sample=self.sample, disposition=self.in_use,
                                   checked_out_by=self.user, checked_out_at=timezone.now())

    def test_the_results_bar_has_an_id(self):
        self.assertEqual(self.html().count('id="results-bar"'), 1)

    def test_the_pills_are_in_the_results_bar_not_the_toolbar(self):
        html = self.html()
        bar_start = html.index('id="results-bar"')
        toolbar = html[html.index('class="toolbar-row"'):bar_start]
        self.assertNotIn('toggle-pill', toolbar)
        bar = self.bar_of(html)
        self.assertEqual(len(re.findall(r'class="toggle-pill(?: on)?"', bar)), 2)
        self.assertIn('Hide exhausted', bar)
        self.assertIn('Checked out by me', bar)

    def test_pills_come_first_then_the_count_and_the_view_toggle(self):
        bar = self.bar()
        order = ['toggle-pills', 'result-count', 'view-toggle']
        positions = [bar.index(token) for token in order]
        self.assertEqual(positions, sorted(positions))

    def test_the_toggle_links_keep_the_page_in_place_with_an_anchor(self):
        response = self.client.get(self.url, {'type': 'aliquot', 'q': 'x', 'sort': 'passage', 'page': '1'})
        for key in ('checked_out_toggle_url', 'hide_finished_toggle_url'):
            with self.subTest(link=key):
                url = response.context[key]
                self.assertTrue(url.endswith('#results-bar'), url)
                self.assertIn('q=x', url)            # still keeps the other parameters
                self.assertIn('sort=passage', url)
                self.assertNotIn('page=', url)       # and still goes back to page 1
        html = response.content.decode()
        self.assertRegex(html, r'href="\?[^"]*checked_out_by=me[^"]*#results-bar"')
        self.assertRegex(html, r'href="\?[^"]*hide_finished=1[^"]*#results-bar"')

    def test_turning_a_pill_off_keeps_the_list_type_and_the_anchor(self):
        response = self.client.get(self.url, {'type': 'aliquot', 'hide_finished': '1'})
        self.assertEqual(response.context['hide_finished_toggle_url'], '?type=aliquot#results-bar')

    def test_the_count_shows_in_the_checked_out_pill_only_while_it_is_off(self):
        self.checked_out(2)
        off = self.bar()
        self.assertRegex(off, r'Checked out by me &middot; 2')
        on = self.bar(checked_out_by='me')
        pill = on[on.index('Checked out by me'):]
        pill = pill[:pill.index('</a>')]
        self.assertNotIn('&middot;', pill)
        self.assertNotRegex(pill, r'\d')

    def test_the_hidden_count_is_still_in_the_accessible_label(self):
        self.checked_out(1)
        self.assertIn('aria-label="Checked out by me, 1 aliquot, off. Select to turn on"', self.bar())
        self.checked_out(1)
        self.assertIn('aria-label="Checked out by me, 2 aliquots, off. Select to turn on"', self.bar())
        self.assertIn('aria-label="Checked out by me, on. Select to turn off"', self.bar(checked_out_by='me'))

    def test_chips_sit_between_the_toolbar_and_the_results_bar_and_only_when_active(self):
        html = self.html(f_sample='test', f_passage='p8')
        positions = [html.index('class="toolbar-row"'), html.index('class="filter-chips"'),
                     html.index('id="results-bar"')]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('class="filter-chips"', self.html())

    def test_clear_all_is_in_the_chips_row_not_the_results_bar(self):
        html = self.html(f_sample='test', f_passage='p8')      # matches nothing, so no table is rendered
        chips = html[html.index('class="filter-chips"'):html.index('id="results-bar"')]
        self.assertIn('Clear all', chips)
        self.assertNotIn('Clear all', self.bar_of(html))

    def test_the_samples_list_keeps_its_own_pill_where_it_was(self):
        html = self.client.get(self.url).content.decode()
        self.assertNotIn('toggle-pill', self.bar_of(html))     # no pills in the Samples results bar
        self.assertIn('Low count &middot;', html)              # the Low count pill is still on the page

    def test_the_bar_exists_on_every_list_for_the_anchor_and_count(self):
        for params in ({}, {'type': 'source'}, {'type': 'aliquot-type'}):
            with self.subTest(params=params):
                html = self.client.get(self.url, params).content.decode()
                self.assertIn('id="results-bar"', html)
                self.assertIn('result-count', html)


class ResultsBarStyleTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_pills_are_at_least_32px_tall(self):
        css = open(finders.find('style.css') or finders.find('krill/style.css')).read()
        rule = css[css.index('.toggle-pill {'):]
        rule = rule[:rule.index('}')]
        self.assertIn('min-height: 32px', rule)

    def test_the_bar_is_a_wrapping_row_centred_with_pills_left_and_info_right(self):
        html = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'}).content.decode()
        rule = html[html.index('.results-header {'):]
        rule = rule[:rule.index('}')]
        for needed in ('display: flex', 'justify-content: space-between', 'align-items: center', 'flex-wrap: wrap'):
            with self.subTest(declaration=needed):
                self.assertIn(needed, rule)
        info = html[html.index('.results-info {'):]
        self.assertIn('margin-left: auto', info[:info.index('}')])

    def test_narrow_screens_wrap_instead_of_stacking_into_a_column(self):
        html = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'}).content.decode()
        media = html[html.index('@media (max-width: 768px)'):]
        media = media[:media.index('\n}\n')]
        self.assertNotRegex(media, r'\.results-header\s*\{[^}]*flex-direction:\s*column')
