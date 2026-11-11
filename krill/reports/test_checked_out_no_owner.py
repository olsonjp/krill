from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from person.models import UserAuditLog
from sample.models.aliquot import Aliquot, AliquotDisposition
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class ReportTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='x')
        self.sample = Sample.objects.create(name='Line A', source=Source.objects.create(name='S'))
        self.disp = {
            kind: AliquotDisposition.objects.get_or_create(name=name, defaults={'disposition_type': kind})[0]
            for kind, name in (('in_use', 'In Use'), ('stored', 'Stored'), ('exhausted', 'Used'))
        }
        self.url = reverse('reports:checked_out_no_owner')

    def _aliquot(self, kind, owner=None, **kwargs):
        return Aliquot.objects.create(
            sample=self.sample, disposition=self.disp[kind],
            checked_out_by=owner, checked_out_at=timezone.now() if owner else None, **kwargs)


class CheckedOutNoOwnerReportTest(ReportTestBase):
    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_lists_only_in_use_aliquots_without_an_owner(self):
        ownerless = self._aliquot('in_use', passage='p6')
        owned = self._aliquot('in_use', owner=self.user)
        stored = self._aliquot('stored')
        used_up = self._aliquot('exhausted')
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['page_obj']), [ownerless])
        self.assertEqual(response.context['total'], 1)
        self.assertContains(response, 'p6')
        self.assertContains(response, '1 aliquot marked In Use')
        for other in (owned, stored, used_up):
            self.assertNotContains(response, f'#{other.id}<')

    def test_empty_state(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), 'No aliquots are checked out without an owner.')

    def test_paginates_at_50(self):
        for _ in range(51):
            self._aliquot('in_use')
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['page_obj']), 50)
        self.assertEqual(response.context['total'], 51)
        self.assertEqual(len(self.client.get(self.url, {'page': 2}).context['page_obj']), 1)

    def test_linked_from_reports_dashboard(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('reports:reports_dashboard')), self.url)


class BulkStatusChangeTest(ReportTestBase):
    """Managers and admins can tick ownerless In Use aliquots and move them to Exhausted or Disposed."""

    def setUp(self):
        super().setUp()
        self.manager = User.objects.create_user(username='mgr', password='x')
        self.manager.role.role = 'lab_manager'
        self.manager.role.save()
        self.disp['disposed'] = AliquotDisposition.objects.get_or_create(
            name='Disposed', defaults={'disposition_type': 'disposed'})[0]

    def _post(self, ids, disposition, **extra):
        return self.client.post(self.url, {'aliquot_ids': ids, 'disposition': disposition.id, **extra})

    def test_controls_shown_to_managers_only(self):
        self._aliquot('in_use')
        self.client.force_login(self.manager)
        manager_page = self.client.get(self.url)
        self.assertTrue(manager_page.context['can_change'])
        self.assertContains(manager_page, 'id="bulkApply"')
        self.assertContains(manager_page, 'name="aliquot_ids"')
        self.client.force_login(self.user)  # lab_member
        member_page = self.client.get(self.url)
        self.assertFalse(member_page.context['can_change'])
        self.assertNotContains(member_page, 'id="bulkApply"')
        self.assertNotContains(member_page, 'name="aliquot_ids"')

    def test_dropdown_offers_only_exhausted_and_disposed(self):
        self.client.force_login(self.manager)
        offered = {d.disposition_type for d in self.client.get(self.url).context['target_dispositions']}
        self.assertEqual(offered, {'exhausted', 'disposed'})

    def test_manager_moves_ticked_aliquots_and_it_is_logged(self):
        a, b, untouched = self._aliquot('in_use'), self._aliquot('in_use'), self._aliquot('in_use')
        self.client.force_login(self.manager)
        response = self._post([a.id, b.id], self.disp['exhausted'], page='1')
        self.assertRedirects(response, self.url + '?page=1', fetch_redirect_response=False)
        for moved in (a, b):
            moved.refresh_from_db()
            self.assertEqual(moved.disposition, self.disp['exhausted'])
        untouched.refresh_from_db()
        self.assertEqual(untouched.disposition.disposition_type, 'in_use')
        self.assertEqual(UserAuditLog.objects.filter(action='aliquot_updated', user=self.manager).count(), 2)
        self.assertContains(self.client.get(self.url), 'Marked 2 aliquots as Used.')

    def test_can_move_to_disposed(self):
        a = self._aliquot('in_use')
        self.client.force_login(self.manager)
        self._post([a.id], self.disp['disposed'])
        a.refresh_from_db()
        self.assertEqual(a.disposition.disposition_type, 'disposed')

    def test_member_cannot_change_status(self):
        a = self._aliquot('in_use')
        self.client.force_login(self.user)
        self.assertEqual(self._post([a.id], self.disp['exhausted']).status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.disposition.disposition_type, 'in_use')

    def test_cannot_move_to_stored_or_in_use(self):
        a = self._aliquot('in_use')
        self.client.force_login(self.manager)
        for kind in ('stored', 'in_use'):
            with self.subTest(target=kind):
                self._post([a.id], self.disp[kind])
                a.refresh_from_db()
                self.assertEqual(a.disposition.disposition_type, 'in_use')

    def test_skips_aliquots_that_are_no_longer_ownerless_in_use(self):
        stale_owned = self._aliquot('in_use', owner=self.user)
        stale_stored = self._aliquot('stored')
        fresh = self._aliquot('in_use')
        self.client.force_login(self.manager)
        self._post([stale_owned.id, stale_stored.id, fresh.id], self.disp['exhausted'])
        stale_owned.refresh_from_db(); stale_stored.refresh_from_db(); fresh.refresh_from_db()
        self.assertEqual(stale_owned.disposition.disposition_type, 'in_use')
        self.assertEqual(stale_stored.disposition.disposition_type, 'stored')
        self.assertEqual(fresh.disposition.disposition_type, 'exhausted')
        self.assertContains(self.client.get(self.url), 'Marked 1 aliquot as Used. 2 skipped')

    def test_nothing_ticked_changes_nothing_and_says_so(self):
        a = self._aliquot('in_use')
        self.client.force_login(self.manager)
        self._post([], self.disp['exhausted'])
        a.refresh_from_db()
        self.assertEqual(a.disposition.disposition_type, 'in_use')
        self.assertContains(self.client.get(self.url), 'Choose at least one aliquot and a status.')

    def test_bad_page_value_in_redirect_is_ignored(self):
        a = self._aliquot('in_use')
        self.client.force_login(self.manager)
        response = self._post([a.id], self.disp['exhausted'], page='//evil.example')
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
