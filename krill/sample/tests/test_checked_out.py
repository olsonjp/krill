from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from ..models.aliquot import Aliquot, AliquotDisposition
from .test_views import SampleViewTest

User = get_user_model()


class CheckoutRecordsOwnerTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]
        self.exhausted = AliquotDisposition.objects.get_or_create(
            name='Used', defaults={'disposition_type': 'exhausted'})[0]

    def _checkout(self, aliquot):
        return self.client.post(
            reverse('sample:aliquot_detail', kwargs={'pk': aliquot.pk}), {'action': 'checkout'})

    def test_checkout_records_who_and_when(self):
        before = timezone.now()
        self._checkout(self.aliquot)
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition.disposition_type, 'in_use')
        self.assertEqual(self.aliquot.checked_out_by, self.user)
        self.assertGreaterEqual(self.aliquot.checked_out_at, before)

    def test_owner_is_kept_after_the_aliquot_is_used_up(self):
        self._checkout(self.aliquot)
        self.aliquot.refresh_from_db()
        self.aliquot.disposition = self.exhausted
        self.aliquot.save()
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.checked_out_by, self.user)
        self.assertIsNotNone(self.aliquot.checked_out_at)

    def test_deleting_the_user_keeps_the_aliquot(self):
        self._checkout(self.aliquot)
        self.user.delete()
        self.aliquot.refresh_from_db()
        self.assertIsNone(self.aliquot.checked_out_by)

    def test_detail_pages_show_who_checked_it_out(self):
        self._checkout(self.aliquot)
        for url in (
            reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': self.aliquot.pk}),
            reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}),
        ):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), 'Checked out by:')
                self.assertContains(self.client.get(url), 'testuser')

    def test_never_checked_out_aliquot_has_no_checked_out_row(self):
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertNotContains(response, 'Checked out by:')


class CheckedOutByMeFilterTest(SampleViewTest):
    def setUp(self):
        super().setUp()
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]
        self.exhausted = AliquotDisposition.objects.get_or_create(
            name='Used', defaults={'disposition_type': 'exhausted'})[0]
        self.other_user = User.objects.create_user(username='colleague', password='x')
        self.client.force_login(self.user)

    def _make(self, owner, disposition=None, **kwargs):
        return Aliquot.objects.create(
            sample=self.sample, aliquot_type=self.aliquot_type,
            disposition=disposition or self.in_use,
            checked_out_by=owner, checked_out_at=timezone.now(), **kwargs)

    def _list(self, **params):
        return self.client.get(reverse('sample:sample_list'), {'type': 'aliquot', 'checked_out_by': 'me', **params})

    def test_lists_only_my_in_use_aliquots(self):
        mine = self._make(self.user, passage='p3')
        self._make(self.other_user)                                  # someone else's
        self._make(self.user, disposition=self.exhausted)             # mine, but exhausted
        Aliquot.objects.create(sample=self.sample, disposition=self.in_use)  # in use, no owner
        response = self._list()
        self.assertEqual(list(response.context['items']), [mine])
        self.assertTrue(response.context['checked_out_by_me'])

    def test_shows_checked_out_time_column_only_when_filtered(self):
        self._make(self.user)
        filtered = self._list()
        self.assertContains(filtered, '<th>Checked Out</th>')
        self.assertContains(filtered, 'name="checked_out_by" value="me"')
        plain = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'})
        self.assertNotContains(plain, '<th>Checked Out</th>')

    def test_works_with_search_and_sort(self):
        keep = self._make(self.user, passage='p8')
        self._make(self.user, passage='p9')
        response = self._list(q='p8', sort='passage')
        self.assertEqual(list(response.context['items']), [keep])

    def test_other_values_are_ignored(self):
        self._make(self.other_user)
        response = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot', 'checked_out_by': str(self.other_user.pk)})
        self.assertFalse(response.context['checked_out_by_me'])
        self.assertEqual(len(response.context['items']), 2)  # nothing filtered: self.aliquot + theirs


class ToggleKeyPillsTest(SampleViewTest):
    """The two yes/no filters are pills (links) under the search bar."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]
        self.exhausted = AliquotDisposition.objects.get_or_create(
            name='Used', defaults={'disposition_type': 'exhausted'})[0]

    def _list(self, **params):
        return self.client.get(reverse('sample:sample_list'), {'type': 'aliquot', **params})

    def test_pills_start_off_with_aria_state(self):
        response = self._list()
        self.assertContains(response, 'aria-label="Checked out by me, 0 aliquots, off. Select to turn on"')
        self.assertContains(response, 'aria-label="Hide exhausted, off. Select to turn on"')
        self.assertNotContains(response, 'toggle-pill on')

    def test_pills_show_on_state_and_turn_off_links(self):
        response = self._list(checked_out_by='me', hide_finished='1')
        self.assertContains(response, 'aria-label="Checked out by me, on. Select to turn off"')
        self.assertContains(response, 'aria-label="Hide exhausted, on. Select to turn off"')
        self.assertEqual(response.content.decode().count('toggle-pill on'), 2)

    def test_toggle_urls_flip_one_param_keep_others_and_reset_page(self):
        response = self._list(q='p8', sort='passage', page='1', hide_finished='1')
        on_url = response.context['checked_out_toggle_url']
        self.assertIn('checked_out_by=me', on_url)
        self.assertIn('hide_finished=1', on_url)
        self.assertIn('q=p8', on_url)
        self.assertIn('sort=passage', on_url)
        self.assertNotIn('page=', on_url)
        off_url = response.context['hide_finished_toggle_url']
        self.assertNotIn('hide_finished', off_url)
        self.assertIn('q=p8', off_url)
        self.assertNotIn('page=', off_url)

    def test_following_a_toggle_link_applies_the_filter(self):
        mine = Aliquot.objects.create(
            sample=self.sample, disposition=self.in_use,
            checked_out_by=self.user, checked_out_at=timezone.now())
        url = self._list().context['checked_out_toggle_url']
        response = self.client.get(reverse('sample:sample_list') + url)
        self.assertEqual(list(response.context['items']), [mine])

    def test_checked_out_pill_counts_my_in_use_aliquots_only(self):
        other = User.objects.create_user(username='colleague', password='x')
        for owner, disp in ((self.user, self.in_use), (self.user, self.in_use),
                            (self.user, self.exhausted), (other, self.in_use)):
            Aliquot.objects.create(sample=self.sample, disposition=disp,
                                   checked_out_by=owner, checked_out_at=timezone.now())
        response = self._list()
        self.assertEqual(response.context['checked_out_count'], 2)
        self.assertContains(response, 'Checked out by me &middot; 2')

    def test_search_button_has_aria_label_and_singular_count(self):
        response = self._list(q='Test Sample')
        self.assertContains(response, 'aria-label="Search"')
        self.assertContains(response, '1 aliquot found')
        self.assertNotContains(response, '1 aliquots found')
