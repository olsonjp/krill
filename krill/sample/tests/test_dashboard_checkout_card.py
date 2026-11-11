from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from person.models import UserAuditLog
from ..models.aliquot import Aliquot, AliquotDisposition, AliquotLocation
from .test_views import SampleViewTest

User = get_user_model()


class CheckoutFixtureMixin:
    def make_dispositions(self):
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]
        self.exhausted = AliquotDisposition.objects.get_or_create(
            name='Used', defaults={'disposition_type': 'exhausted'})[0]

    def checked_out(self, owner, hours_ago=1, **kwargs):
        return Aliquot.objects.create(
            sample=self.sample, aliquot_type=self.aliquot_type, disposition=self.in_use,
            checked_out_by=owner, checked_out_at=timezone.now() - timedelta(hours=hours_ago), **kwargs)


class DashboardCheckedOutCardTest(CheckoutFixtureMixin, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.make_dispositions()
        self.client.force_login(self.user)
        self.other = User.objects.create_user(username='colleague', password='x')

    def _home(self):
        return self.client.get(reverse('home'))

    def test_lists_only_my_in_use_aliquots_newest_first(self):
        old = self.checked_out(self.user, hours_ago=48)
        new = self.checked_out(self.user, hours_ago=1)
        self.checked_out(self.other)                                   # someone else's
        used_up = self.checked_out(self.user)
        used_up.disposition = self.exhausted
        used_up.save()
        Aliquot.objects.create(sample=self.sample, disposition=self.in_use)  # no owner
        response = self._home()
        self.assertEqual([r['aliquot'] for r in response.context['checked_out']['items']], [new, old])
        self.assertEqual(response.context['checked_out']['total'], 2)
        self.assertContains(response, 'Checked out by you (2)')

    def test_shows_at_most_five_rows_but_counts_all(self):
        for hours in range(1, 8):
            self.checked_out(self.user, hours_ago=hours)
        checked_out = self._home().context['checked_out']
        self.assertEqual(len(checked_out['items']), 5)
        self.assertEqual(checked_out['total'], 7)
        self.assertContains(self._home(), 'Checked out by you (7)')

    def test_row_shows_details_children_and_actions(self):
        parent = self.checked_out(self.user, hours_ago=50, passage='p12')
        Aliquot.objects.create(sample=self.sample, parent=parent, disposition=self.stored_disposition)
        Aliquot.objects.create(sample=self.sample, parent=parent, disposition=self.stored_disposition)
        response = self._home()
        self.assertContains(response, f'Test Sample #{parent.id}')
        self.assertContains(response, 'Test Type')
        self.assertContains(response, 'p12')
        self.assertContains(response, 'out 2 days ago')
        self.assertContains(response, '2 children')
        self.assertContains(response, f'?type=aliquot&parent={parent.id}&next=/')
        self.assertContains(response, 'name="action" value="done"')
        self.assertContains(response, reverse('sample:aliquot_detail', kwargs={'pk': parent.id}))
        self.assertContains(response, '?type=aliquot&checked_out_by=me')

    def test_singular_child_and_zero_children(self):
        one = self.checked_out(self.user, hours_ago=2)
        Aliquot.objects.create(sample=self.sample, parent=one, disposition=self.stored_disposition)
        self.checked_out(self.user, hours_ago=1)
        response = self._home()
        self.assertContains(response, '1 child<')
        self.assertContains(response, '0 children')

    def test_card_sits_above_freezers(self):
        self.checked_out(self.user)
        html = self._home().content.decode()
        self.assertLess(html.index('Checked out by you'), html.index('<h2>Freezers</h2>'))

    def test_empty_state_is_one_line_with_a_find_link(self):
        response = self._home()
        self.assertContains(response, 'Nothing checked out.')
        self.assertContains(response, 'Find an aliquot')
        self.assertNotContains(response, 'Checked out by you (')


class CreateChildFlowTest(CheckoutFixtureMixin, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.make_dispositions()
        self.client.force_login(self.user)
        self.parent = self.checked_out(self.user, passage='p8')
        self.url = reverse('sample:sample_create')

    def _get(self, **params):
        return self.client.get(self.url, {'type': 'aliquot', 'parent': self.parent.id, **params})

    def _post(self, extra=None, query=''):
        data = {
            'parent': self.parent.id, 'sample': self.sample.id, 'aliquot_type': self.aliquot_type.id,
            'disposition': self.stored_disposition.id, 'access_level': 'all_members',
            'passage': 'p9', 'count': 1, **(extra or {}),
        }
        return self.client.post(f'{self.url}?type=aliquot&parent={self.parent.id}{query}', data)

    def test_form_prefills_sample_type_and_passage(self):
        initial = self._get().context['form'].initial
        self.assertEqual(initial['sample'], self.sample.id)
        self.assertEqual(initial['aliquot_type'], self.aliquot_type.id)
        self.assertEqual(initial['passage'], 'p8')

    def test_used_up_checkbox_is_on_by_default_for_an_in_use_parent(self):
        response = self._get()
        self.assertEqual(response.context['parent_aliquot'], self.parent)
        self.assertContains(response, 'name="parent_used_up" value="1" checked')
        # The form hides the real checkbox and draws a box from this span; without it nothing is visible
        self.assertRegex(response.content.decode(), r'name="parent_used_up"[^>]*>\s*<span class="checkbox-custom"></span>')

    def test_no_checkbox_without_parent_or_for_a_stored_parent(self):
        self.assertNotContains(self.client.get(self.url, {'type': 'aliquot'}), 'parent_used_up')
        stored_parent = Aliquot.objects.create(sample=self.sample, disposition=self.stored_disposition)
        self.assertNotContains(self._get(parent=stored_parent.id), 'parent_used_up')

    def test_ticked_box_marks_parent_exhausted_and_logs_it(self):
        response = self._post({'parent_used_up': '1'})
        self.assertEqual(response.status_code, 302)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.disposition, self.exhausted)
        child = Aliquot.objects.get(parent=self.parent)
        self.assertEqual(child.passage, 'p9')
        self.assertTrue(UserAuditLog.objects.filter(
            action='aliquot_updated', target_id=self.parent.id, user=self.user).exists())

    def test_unticked_box_leaves_parent_in_use(self):
        self._post()
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.disposition, self.in_use)
        self.assertTrue(Aliquot.objects.filter(parent=self.parent).exists())

    def test_ticked_box_is_ignored_for_a_stored_parent(self):
        stored_parent = Aliquot.objects.create(sample=self.sample, disposition=self.stored_disposition)
        self.client.post(
            f'{self.url}?type=aliquot&parent={stored_parent.id}',
            {'parent': stored_parent.id, 'sample': self.sample.id, 'aliquot_type': self.aliquot_type.id,
             'disposition': self.stored_disposition.id, 'access_level': 'all_members', 'count': 1,
             'parent_used_up': '1'})
        stored_parent.refresh_from_db()
        self.assertEqual(stored_parent.disposition, self.stored_disposition)

    def test_returns_to_dashboard_when_next_is_given(self):
        response = self._post(query='&next=/')
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_default_return_is_the_aliquot_list_and_foreign_next_is_ignored(self):
        default = reverse('sample:sample_list') + '?type=aliquot'
        self.assertRedirects(self._post(), default, fetch_redirect_response=False)
        self.assertRedirects(self._post(query='&next=https://evil.example/'), default, fetch_redirect_response=False)

    def test_cancel_goes_back_to_next(self):
        self.assertContains(self._get(next='/'), "window.location.href='/'")


class DoneActionTest(CheckoutFixtureMixin, SampleViewTest):
    def setUp(self):
        super().setUp()
        self.make_dispositions()
        self.client.force_login(self.user)
        self.aliquot = self.checked_out(self.user)
        self.url = reverse('sample:aliquot_detail', kwargs={'pk': self.aliquot.pk})

    def test_done_marks_exhausted_logs_and_returns_to_next(self):
        response = self.client.post(self.url, {'action': 'done', 'next': '/'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.exhausted)
        self.assertEqual(self.aliquot.checked_out_by, self.user)  # kept as the record
        self.assertTrue(UserAuditLog.objects.filter(action='aliquot_updated', target_id=self.aliquot.id).exists())

    def test_done_without_next_returns_to_the_aliquot_page(self):
        self.assertRedirects(self.client.post(self.url, {'action': 'done'}), self.url, fetch_redirect_response=False)

    def test_foreign_next_is_ignored(self):
        response = self.client.post(self.url, {'action': 'done', 'next': 'https://evil.example/'})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)

    def test_done_does_nothing_to_an_aliquot_that_is_not_in_use(self):
        stored = Aliquot.objects.create(sample=self.sample, disposition=self.stored_disposition)
        self.client.post(reverse('sample:aliquot_detail', kwargs={'pk': stored.pk}), {'action': 'done'})
        stored.refresh_from_db()
        self.assertEqual(stored.disposition, self.stored_disposition)

    def test_done_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'action': 'done'}).status_code, 302)
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.in_use)


class MarkExhaustedTest(CheckoutFixtureMixin, SampleViewTest):
    def test_uses_an_existing_exhausted_disposition(self):
        self.make_dispositions()
        self.aliquot.mark_exhausted()
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition, self.exhausted)

    def test_creates_one_when_none_exists(self):
        self.assertFalse(AliquotDisposition.objects.filter(disposition_type='exhausted').exists())
        self.aliquot.mark_exhausted()
        self.aliquot.refresh_from_db()
        self.assertEqual(self.aliquot.disposition.disposition_type, 'exhausted')

    def test_frees_the_box_slot(self):
        self.aliquot.store_in_location(self.box, 1, 1)
        self.aliquot.mark_exhausted()
        self.assertFalse(AliquotLocation.objects.filter(aliquot=self.aliquot).exists())
