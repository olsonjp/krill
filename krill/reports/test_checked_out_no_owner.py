from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from sample.models.aliquot import Aliquot, AliquotDisposition
from sample.models.sample import Sample
from sample.models.source import Source

User = get_user_model()


class CheckedOutNoOwnerReportTest(TestCase):
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
