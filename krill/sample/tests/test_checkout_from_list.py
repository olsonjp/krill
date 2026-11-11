from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from ..models.aliquot import Aliquot, AliquotDisposition, AliquotLocation
from .test_views import SampleViewTest

User = get_user_model()


class CheckoutFixture:
    def setup_dispositions(self):
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]
        self.exhausted = AliquotDisposition.objects.get_or_create(
            name='Used', defaults={'disposition_type': 'exhausted'})[0]

    def make_manager(self, username='mgr'):
        manager = User.objects.create_user(username=username, password='x')
        manager.role.role = 'lab_manager'
        manager.role.save()
        return manager

    def out(self, owner, **kwargs):
        return Aliquot.objects.create(
            sample=self.sample, disposition=self.in_use,
            checked_out_by=owner, checked_out_at=timezone.now(), **kwargs)


class CheckOutButtonOnListTest(CheckoutFixture, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.setup_dispositions()
        self.client.force_login(self.user)
        self.list_url = reverse('sample:sample_list')

    def _list(self, **params):
        return self.client.get(self.list_url, {'type': 'aliquot', **params})

    def test_button_only_on_stored_rows(self):
        in_use = Aliquot.objects.create(sample=self.sample, disposition=self.in_use)
        exhausted = Aliquot.objects.create(sample=self.sample, disposition=self.exhausted)
        response = self._list()
        html = response.content.decode()
        self.assertEqual(html.count('name="action" value="checkout"'), 1)  # only self.aliquot is stored
        self.assertContains(response, reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        for other in (in_use, exhausted):
            self.assertNotContains(response, f'action="{reverse("sample:aliquot_detail", kwargs={"pk": other.pk})}"')

    def test_form_returns_to_the_current_list_view(self):
        response = self._list(q='Test', sort='passage')
        self.assertContains(response, 'name="next" value="/samples/list/?type=aliquot&amp;q=Test&amp;sort=passage"')

    def test_checkout_from_list_records_owner_and_returns_to_the_list(self):
        url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk})
        back = self.list_url + '?type=aliquot&q=Test'
        response = self.client.post(url, {'action': 'checkout', 'next': back})
        self.assertRedirects(response, back, fetch_redirect_response=False)
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition.disposition_type, 'in_use')
        self.assertEqual(self.aliquot.checked_out_by, self.user)

    def test_checkout_without_next_still_goes_to_the_aliquot_page(self):
        url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk})
        self.assertRedirects(self.client.post(url, {'action': 'checkout'}), url, fetch_redirect_response=False)

    def test_foreign_next_is_ignored(self):
        url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk})
        response = self.client.post(url, {'action': 'checkout', 'next': 'https://evil.example/'})
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_stale_checkout_does_not_take_over_someone_elses_aliquot(self):
        colleague = User.objects.create_user(username='colleague', password='x')
        taken = self.out(colleague)
        self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': taken.pk}), {'action': 'checkout'})
        taken.refresh_from_db()
        self.assertEqual(taken.checked_out_by, colleague)

    def test_checkout_frees_the_box_position(self):
        self.aliquot.store_in_location(self.box, 1, 1)
        self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}), {'action': 'checkout'})
        self.assertFalse(AliquotLocation.objects.filter(aliquot=self.aliquot).exists())


class CheckedOutByEveryoneFilterTest(CheckoutFixture, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.setup_dispositions()
        self.manager = self.make_manager()
        self.other = User.objects.create_user(username='aaa_colleague', password='x', first_name='Ada', last_name='Lovelace')

    def _list(self, **params):
        return self.client.get(reverse('sample:sample_list'), {'type': 'aliquot', 'checked_out_by': 'all', **params})

    def test_manager_sees_every_owned_in_use_aliquot_grouped_by_person(self):
        self.client.force_login(self.manager)
        mine = self.out(self.manager)
        theirs = self.out(self.other)
        ownerless = Aliquot.objects.create(sample=self.sample, disposition=self.in_use)
        used_up = self.out(self.other)
        used_up.disposition = self.exhausted
        used_up.save()
        response = self._list()
        items = list(response.context['items'])
        self.assertTrue(response.context['checked_out_all'])
        self.assertNotIn(ownerless, items)
        self.assertNotIn(used_up, items)
        self.assertIn(mine, items)
        self.assertIn(theirs, items)
        # grouped by owner username: aaa_colleague before mgr
        owners = [a.checked_out_by.username for a in items]
        self.assertEqual(owners, sorted(owners))

    def test_shows_who_and_chip_and_columns(self):
        self.client.force_login(self.manager)
        self.out(self.other)
        response = self._list()
        self.assertContains(response, '<th>Checked Out By</th>')
        self.assertContains(response, '<th>Checked Out</th>')
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, 'Checked out by anyone')
        self.assertContains(response, 'name="checked_out_by" value="all"')

    def test_members_cannot_use_the_all_filter(self):
        self.client.force_login(self.user)  # lab_member
        theirs = self.out(self.other)
        response = self._list()
        self.assertFalse(response.context['checked_out_all'])
        self.assertIn(self.aliquot, response.context['items'])   # not filtered at all
        self.assertIn(theirs, response.context['items'])
        self.assertNotContains(response, '<th>Checked Out By</th>')

    def test_an_explicit_sort_overrides_the_grouping(self):
        self.client.force_login(self.manager)
        a = self.out(self.manager, passage='p1')
        b = self.out(self.other, passage='p2')
        items = list(self._list(sort='passage', order='desc').context['items'])
        self.assertEqual(items, [b, a])

    def test_me_pill_switches_from_all_to_me(self):
        self.client.force_login(self.manager)
        self.assertIn('checked_out_by=me', self._list().context['checked_out_toggle_url'])


class LabCheckoutsTileTest(CheckoutFixture, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.setup_dispositions()
        self.manager = self.make_manager()
        self.other = User.objects.create_user(username='colleague', password='x')

    def test_manager_sees_the_tile_with_counts_and_link(self):
        self.out(self.manager)
        self.out(self.other)
        self.out(self.other)
        self.client.force_login(self.manager)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['lab_checkouts'], {'aliquots': 3, 'people': 2})
        self.assertContains(response, 'Lab Checkouts')
        self.assertContains(response, '3 aliquots &middot; 2 people')
        self.assertContains(response, '?type=aliquot&checked_out_by=all')

    def test_singular_forms(self):
        self.out(self.other)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse('home')), '1 aliquot &middot; 1 person')

    def test_tile_counts_only_owned_in_use_aliquots(self):
        Aliquot.objects.create(sample=self.sample, disposition=self.in_use)  # no owner
        used_up = self.out(self.other)
        used_up.disposition = self.exhausted
        used_up.save()
        self.client.force_login(self.manager)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['lab_checkouts'], {'aliquots': 0, 'people': 0})
        self.assertContains(response, 'None checked out')

    def test_members_do_not_get_the_tile(self):
        self.out(self.other)
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertIsNone(response.context['lab_checkouts'])
        self.assertNotContains(response, 'Lab Checkouts')


class ConfirmDialogMarkupTest(CheckoutFixture, SampleViewTest):
    """Confirmations use the in-page dialog (data-confirm), not the browser's confirm() popup."""

    def setUp(self):
        super().setUp()
        self.setup_dispositions()
        self.client.force_login(self.user)

    def test_layout_loads_the_dialog_script(self):
        self.assertContains(self.client.get(reverse('home')), 'js/confirm-dialog.js')

    def test_list_check_out_form_has_message_and_label(self):
        response = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'})
        self.assertContains(
            response,
            f'data-confirm="Check out Test Sample #{self.aliquot.id}? This changes its status to In Use and frees its box position."',
        )
        self.assertContains(response, 'data-confirm-label="Check out"')
        self.assertNotContains(response, 'onclick="return confirm(')

    def test_aliquot_page_check_out_form_has_message(self):
        response = self.client.get(reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk}))
        self.assertContains(response, 'data-confirm="Check out this aliquot? This will change its status to In Use."')
        self.assertNotContains(response, 'onclick="return confirm(')

    def test_dashboard_done_form_has_message_and_label(self):
        owned = self.out(self.user)
        response = self.client.get(reverse('home'))
        self.assertContains(
            response,
            f'data-confirm="Mark Test Sample #{owned.id} as exhausted, with no child recorded?"',
        )
        self.assertContains(response, 'data-confirm-label="Mark exhausted"')
        self.assertNotContains(response, 'onclick="return confirm(')

    def test_names_with_quotes_are_escaped_in_the_attribute(self):
        self.sample.name = 'Line "A" <b>'
        self.sample.save()
        html = self.client.get(reverse('sample:sample_list'), {'type': 'aliquot'}).content.decode()
        self.assertIn('data-confirm="Check out Line &quot;A&quot; &lt;b&gt; #', html)
