from django.contrib.auth import get_user_model
from django.urls import reverse

from person.models import SiteConfiguration, UserAuditLog
from reports import attention
from .. import low_count
from ..forms import SampleForm
from ..models.aliquot import Aliquot, AliquotDisposition
from ..models.sample import Sample
from .test_views import SampleViewTest

User = get_user_model()


class LowCountFixture(SampleViewTest):
    """The base fixture's 'Test Sample' has one stored aliquot; start each test from a clean slate."""

    def setUp(self):
        super().setUp()
        Aliquot.objects.all().delete()
        self.in_use = self.disp('In Use', 'in_use')
        self.exhausted = self.disp('Used', 'exhausted')
        self.disposed = self.disp('Disposed', 'disposed')

    def disp(self, name, kind):
        return AliquotDisposition.objects.get_or_create(name=name, defaults={'disposition_type': kind})[0]

    def stored(self, sample, n):
        return [Aliquot.objects.create(sample=sample, disposition=self.stored_disposition) for _ in range(n)]

    def make_sample(self, name, **kwargs):
        return Sample.objects.create(name=name, source=self.source, **kwargs)

    def annotated(self, sample):
        return Sample.objects.with_stored_count().get(pk=sample.pk)

    def login_as(self, role):
        user = User.objects.create_user(username=f'{role}-user', password='x')
        user.role.role = role
        user.role.save()
        self.client.force_login(user)
        return user


class CountingRulesTest(LowCountFixture):
    def test_only_the_stored_disposition_counts(self):
        self.stored(self.sample, 2)
        Aliquot.objects.create(sample=self.sample, disposition=self.in_use)
        Aliquot.objects.create(sample=self.sample, disposition=self.exhausted)
        Aliquot.objects.create(sample=self.sample, disposition=self.disposed)
        counted = self.annotated(self.sample)
        self.assertEqual((counted.stored_count, counted.aliquot_total), (2, 5))

    def test_a_box_position_is_not_required(self):
        placed, unplaced = self.stored(self.sample, 2)
        placed.store_in_location(self.box, 1, 1)
        self.assertEqual(self.annotated(self.sample).stored_count, 2)

    def test_soft_deleted_aliquots_are_ignored(self):
        kept, gone = self.stored(self.sample, 2)
        gone.deleted = True
        gone.save()
        counted = self.annotated(self.sample)
        self.assertEqual((counted.stored_count, counted.aliquot_total), (1, 1))

    def test_counts_do_not_leak_between_samples(self):
        other = self.make_sample('Other')
        self.stored(self.sample, 3)
        self.stored(other, 7)
        self.assertEqual(self.annotated(self.sample).stored_count, 3)
        self.assertEqual(self.annotated(other).stored_count, 7)

    def test_a_sample_with_no_aliquots_at_all_is_not_checked(self):
        counted = self.annotated(self.sample)
        self.assertEqual(counted.aliquot_total, 0)
        self.assertIsNone(low_count.state_for(counted))
        self.assertEqual(low_count.low_samples(), [])

    def test_a_sample_whose_aliquots_are_all_used_up_is_an_alert_at_zero(self):
        Aliquot.objects.create(sample=self.sample, disposition=self.exhausted)
        counted = self.annotated(self.sample)
        self.assertEqual(counted.stored_count, 0)
        self.assertEqual(low_count.state_for(counted), 'alert')


class LevelsAndBoundariesTest(LowCountFixture):
    def test_lab_defaults_are_warn_5_alert_3(self):
        config = SiteConfiguration.load()
        self.assertEqual((config.low_count_warn, config.low_count_alert), (5, 3))
        self.assertEqual(low_count.levels_for(self.sample), (5, 3))

    def test_alert_at_or_below_the_alert_level_and_warn_at_or_below_the_warn_level(self):
        expected = {0: 'alert', 3: 'alert', 4: 'warn', 5: 'warn', 6: None, 20: None}
        for count, state in expected.items():
            with self.subTest(count=count):
                self.assertEqual(low_count.state_for_count(count, 5, 3), state)

    def test_changing_the_lab_defaults_changes_the_result(self):
        self.stored(self.sample, 5)
        self.assertEqual(low_count.state_for(self.annotated(self.sample)), 'warn')
        config = SiteConfiguration.load()
        config.low_count_warn, config.low_count_alert = 6, 5
        config.save()
        self.assertEqual(low_count.state_for(self.annotated(self.sample)), 'alert')

    def test_a_sample_can_override_either_level(self):
        sample = self.make_sample('Own levels', low_count_warn=10, low_count_alert=8)
        self.assertEqual(low_count.levels_for(sample), (10, 8))
        only_warn = self.make_sample('Only warn', low_count_warn=2)
        self.assertEqual(low_count.levels_for(only_warn), (2, 2))   # default alert 3 is capped to the warn level

    def test_override_applies_to_the_state(self):
        sample = self.make_sample('Relaxed', low_count_warn=1, low_count_alert=0)
        self.stored(sample, 3)
        self.assertIsNone(low_count.state_for(self.annotated(sample)))   # 3 is above its warn level of 1


class LowSamplesTest(LowCountFixture):
    def test_lists_only_low_samples_with_their_counts_and_levels(self):
        low = self.make_sample('Low')
        fine = self.make_sample('Fine')
        self.stored(low, 2)
        self.stored(fine, 9)
        [row] = low_count.low_samples()
        self.assertEqual((row['sample'], row['count'], row['warn'], row['alert'], row['state'], row['silenced']),
                         (low, 2, 5, 3, 'alert', False))

    def test_opted_out_samples_are_listed_as_silenced(self):
        quiet = self.make_sample('Quiet', low_count_check=False)
        self.stored(quiet, 1)
        [row] = low_count.low_samples()
        self.assertTrue(row['silenced'])


class AttentionSourceTest(LowCountFixture):
    def _items(self):
        return attention.low_count_items()

    def test_item_fields(self):
        self.stored(self.sample, 4)
        [item] = self._items()
        self.assertEqual(item.key, f'low_count:sample:{self.sample.pk}')
        self.assertEqual(item.title, 'Test Sample')
        self.assertEqual(item.detail, '4 stored aliquots left (alert at 3 or fewer, warn at 5 or fewer)')
        self.assertEqual(item.level, 'warn')
        self.assertEqual(item.url, reverse('sample:detail', kwargs={'type': 'sample', 'pk': self.sample.pk}))
        self.assertEqual((item.target_type, item.target_id, item.silenced), ('sample', self.sample.pk, False))

    def test_wording_for_one_and_for_none(self):
        self.stored(self.sample, 1)
        self.assertIn('1 stored aliquot left', self._items()[0].detail)
        other = self.make_sample('Empty')
        Aliquot.objects.create(sample=other, disposition=self.exhausted)
        details = {i.title: i.detail for i in self._items()}
        self.assertTrue(details['Empty'].startswith('No stored aliquots left'))

    def test_levels(self):
        low, mid = self.make_sample('Low'), self.make_sample('Mid')
        self.stored(low, 3)
        self.stored(mid, 5)
        levels = {i.title: i.level for i in self._items()}
        self.assertEqual(levels, {'Low': 'alert', 'Mid': 'warn'})

    def test_silenced_when_the_check_is_off_and_not_counted(self):
        self.stored(self.sample, 2)
        self.sample.low_count_check = False
        self.sample.save()
        self.assertTrue(self._items()[0].silenced)
        self.assertEqual(attention.summary(), {'count': 0, 'level': None})

    def test_summary_counts_unsilenced_low_samples_and_takes_the_worst_level(self):
        a, b = self.make_sample('A'), self.make_sample('B')
        self.stored(a, 5)
        self.stored(b, 1)
        self.assertEqual(attention.summary(), {'count': 2, 'level': 'alert'})

    def test_silence_and_unsilence_via_the_shared_helper(self):
        self.stored(self.sample, 2)
        self.assertTrue(attention.silence('sample', self.sample.pk, True))
        self.sample.refresh_from_db()
        self.assertFalse(self.sample.low_count_check)
        self.assertTrue(attention.silence('sample', self.sample.pk, False))
        self.sample.refresh_from_db()
        self.assertTrue(self.sample.low_count_check)
        self.assertFalse(attention.silence('sample', 99999, True))

    def test_overview_page_group_item_and_silence_flow(self):
        self.stored(self.sample, 2)
        self.login_as('lab_manager')
        page = self.client.get(reverse('reports:alert_list'))
        self.assertContains(page, 'Low sample counts (1)')
        self.assertContains(page, 'Test Sample')
        self.assertContains(page, 'name="target_type" value="sample"')
        response = self.client.post(reverse('reports:silence_attention'),
                                    {'target_type': 'sample', 'target_id': self.sample.pk, 'silenced': '1'})
        self.assertRedirects(response, reverse('reports:alert_list'), fetch_redirect_response=False)
        self.sample.refresh_from_db()
        self.assertFalse(self.sample.low_count_check)
        after = self.client.get(reverse('reports:alert_list'))
        self.assertContains(after, 'Low sample counts (0)')
        self.assertContains(after, 'Silenced (1)')
        self.assertTrue(UserAuditLog.objects.filter(action='alerts_silenced', target_type='Sample').exists())

    def test_pill_counts_low_samples(self):
        self.stored(self.sample, 2)
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['attention'], {'count': 1, 'level': 'alert'})
        self.assertContains(response, 'class="header-alerts level-alert"')


class SamplesListTest(LowCountFixture):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.url = reverse('sample:sample_list')

    def test_stored_column_and_badges(self):
        alert, warn, fine, quiet = (self.make_sample(n) for n in ('Alert', 'Warn', 'Fine', 'Quiet'))
        quiet.low_count_check = False
        quiet.save()
        for sample, n in ((alert, 2), (warn, 5), (fine, 12), (quiet, 1)):
            self.stored(sample, n)
        response = self.client.get(self.url)
        html = response.content.decode()
        self.assertIn('<th data-sort="stored"', html)
        self.assertEqual(html.count('class="low-badge alert"'), 1)
        self.assertEqual(html.count('class="low-badge warn"'), 1)
        self.assertEqual(html.count('class="low-badge silenced"'), 1)
        states = {s.name: s.low_state for s in response.context['items']}
        self.assertEqual(states, {'Alert': 'alert', 'Fine': None, 'Quiet': 'alert', 'Warn': 'warn',
                                  'Test Sample': None})

    def test_samples_without_aliquots_show_zero_and_no_badge(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'class="low-badge')
        self.assertEqual(response.context['items'][0].stored_count, 0)

    def test_low_count_filter_keeps_only_active_low_samples(self):
        low, fine, quiet, relaxed = (self.make_sample(n) for n in ('Low', 'Fine', 'Quiet', 'Relaxed'))
        quiet.low_count_check = False
        quiet.save()
        relaxed.low_count_warn, relaxed.low_count_alert = 1, 0
        relaxed.save()
        for sample, n in ((low, 4), (fine, 9), (quiet, 1), (relaxed, 3)):
            self.stored(sample, n)
        response = self.client.get(self.url, {'low_count': '1'})
        self.assertEqual([s.name for s in response.context['items']], ['Low'])
        self.assertTrue(response.context['low_count_on'])

    def test_pill_shows_the_count_and_toggles(self):
        self.stored(self.make_sample('Low'), 2)
        off = self.client.get(self.url)
        self.assertEqual(off.context['low_count_pill_count'], 1)
        self.assertContains(off, 'Low count &middot; 1')
        self.assertContains(off, 'aria-label="Low count, off. Select to turn on"')
        self.assertIn('low_count=1', off.context['low_count_toggle_url'])
        on = self.client.get(self.url, {'low_count': '1', 'q': 'Low', 'page': '1'})
        self.assertContains(on, 'aria-label="Low count, on. Select to turn off"')
        self.assertContains(on, '<input type="hidden" name="low_count" value="1">')
        self.assertNotIn('low_count', on.context['low_count_toggle_url'])
        self.assertIn('q=Low', on.context['low_count_toggle_url'])
        self.assertNotIn('page=', on.context['low_count_toggle_url'])

    def test_empty_message_when_nothing_is_low(self):
        self.stored(self.make_sample('Fine'), 12)
        self.assertContains(self.client.get(self.url, {'low_count': '1'}), 'No samples are running low.')

    def test_sort_by_stored_count(self):
        few, many = self.make_sample('Few'), self.make_sample('Many')
        self.stored(few, 1)
        self.stored(many, 8)
        asc = [s.name for s in self.client.get(self.url, {'sort': 'stored', 'order': 'asc'}).context['items']]
        desc = [s.name for s in self.client.get(self.url, {'sort': 'stored', 'order': 'desc'}).context['items']]
        self.assertEqual(asc, ['Test Sample', 'Few', 'Many'])
        self.assertEqual(desc, ['Many', 'Few', 'Test Sample'])

    def test_other_list_types_are_unaffected(self):
        self.assertEqual(self.client.get(self.url, {'type': 'source'}).status_code, 200)
        self.assertNotContains(self.client.get(self.url, {'type': 'aliquot'}), 'Low count &middot;')


class SamplePageTest(LowCountFixture):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.url = reverse('sample:detail', kwargs={'type': 'sample', 'pk': self.sample.pk})

    def test_shows_count_badge_and_levels(self):
        self.stored(self.sample, 4)
        response = self.client.get(self.url)
        self.assertEqual(response.context['low_count'],
                         {'count': 4, 'warn': 5, 'alert': 3, 'state': 'warn', 'enabled': True})
        self.assertContains(response, 'Stored aliquots:')
        self.assertContains(response, 'class="low-badge warn"')
        self.assertContains(response, 'On: warn at 5 or fewer, alert at 3 or fewer')

    def test_no_badge_when_comfortably_stocked(self):
        self.stored(self.sample, 10)
        self.assertNotContains(self.client.get(self.url), 'class="low-badge')

    def test_opted_out_sample_says_so_and_shows_no_badge(self):
        self.stored(self.sample, 1)
        self.sample.low_count_check = False
        self.sample.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'Off for this sample')
        self.assertNotContains(response, 'class="low-badge')

    def test_count_matches_the_remaining_list(self):
        self.stored(self.sample, 3)
        response = self.client.get(self.url)
        self.assertEqual(response.context['low_count']['count'], response.context['remaining_count'])


class SampleFormTest(LowCountFixture):
    def _form(self, **extra):
        data = {'name': 'S', 'source': self.source.pk, 'access_level': 'all_members',
                'low_count_check': 'on', **extra}
        return SampleForm(data)

    def test_overrides_are_optional(self):
        self.assertTrue(self._form().is_valid())

    def test_valid_overrides_are_saved(self):
        form = self._form(low_count_warn='8', low_count_alert='4')
        self.assertTrue(form.is_valid(), form.errors)
        sample = form.save()
        self.assertEqual((sample.low_count_warn, sample.low_count_alert), (8, 4))

    def test_alert_above_warn_is_rejected(self):
        form = self._form(low_count_warn='3', low_count_alert='5')
        self.assertFalse(form.is_valid())
        self.assertIn('low_count_alert', form.errors)

    def test_negative_numbers_are_rejected(self):
        self.assertFalse(self._form(low_count_warn='-1').is_valid())

    def test_unticking_turns_the_check_off(self):
        data = {'name': 'S', 'source': self.source.pk, 'access_level': 'all_members'}
        form = SampleForm(data)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.save().low_count_check)

    def test_editing_a_sample_through_its_page_saves_the_low_count_fields(self):
        self.client.force_login(self.user)
        url = reverse('sample:detail', kwargs={'type': 'sample', 'pk': self.sample.pk})
        self.client.post(url, {'name': 'Test Sample', 'source': self.source.pk, 'access_level': 'all_members',
                               'low_count_warn': '9', 'low_count_alert': '2'})
        self.sample.refresh_from_db()
        self.assertEqual((self.sample.low_count_warn, self.sample.low_count_alert, self.sample.low_count_check),
                         (9, 2, False))


class SettingsLevelsTest(LowCountFixture):
    def setUp(self):
        super().setUp()
        self.url = reverse('settings')

    def _post(self, warn, alert, **extra):
        return self.client.post(self.url, {'form': 'alert_levels', 'low_count_warn': warn,
                                           'low_count_alert': alert, **extra})

    def test_admin_sees_the_form_with_current_values(self):
        self.login_as('lab_admin')
        response = self.client.get(self.url)
        self.assertContains(response, 'id="alert-levels-form"')
        self.assertContains(response, 'name="low_count_warn"')
        self.assertContains(response, 'value="5"')

    def test_members_do_not_see_the_form(self):
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(self.url), 'id="alert-levels-form"')

    def test_admin_saves_new_levels_and_it_is_logged_and_shown(self):
        admin = self.login_as('lab_admin')
        response = self._post('6', '4')
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        config = SiteConfiguration.load()
        self.assertEqual((config.low_count_warn, config.low_count_alert, config.updated_by), (6, 4, admin))
        self.assertTrue(UserAuditLog.objects.filter(user=admin, target_type='SiteConfiguration').exists())
        self.assertContains(self.client.get(self.url), 'Low-count levels saved: warn at 6 or fewer, alert at 4 or fewer.')

    def test_saving_levels_does_not_touch_the_feature_switches(self):
        config = SiteConfiguration.load()
        config.consumables_enabled = True
        config.consumables_ordering_enabled = True
        config.save()
        self.login_as('lab_admin')
        self._post('7', '2')
        config.refresh_from_db()
        self.assertTrue(config.consumables_enabled and config.consumables_ordering_enabled)

    def test_saving_the_feature_switches_does_not_touch_the_levels(self):
        config = SiteConfiguration.load()
        config.low_count_warn, config.low_count_alert = 9, 6
        config.save()
        self.login_as('lab_admin')
        self.client.post(self.url, {'consumables_enabled': 'on'})
        config.refresh_from_db()
        self.assertEqual((config.low_count_warn, config.low_count_alert, config.consumables_enabled), (9, 6, True))

    def test_invalid_levels_are_refused_with_a_message(self):
        self.login_as('lab_admin')
        for warn, alert, message in (('3', '5', 'cannot be higher'), ('x', '1', 'whole numbers'),
                                     ('-1', '1', 'whole numbers'), ('', '', 'whole numbers')):
            with self.subTest(warn=warn, alert=alert):
                self._post(warn, alert)
                self.assertContains(self.client.get(self.url), message)
                config = SiteConfiguration.load()
                self.assertEqual((config.low_count_warn, config.low_count_alert), (5, 3))

    def test_non_admins_cannot_change_the_levels(self):
        self.login_as('lab_manager')
        self.assertEqual(self._post('9', '8').status_code, 403)
        self.assertEqual(SiteConfiguration.load().low_count_warn, 5)
