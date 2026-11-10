import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from krill.views.home import fill_level
from person.models import UserAuditLog
from reports.models import Report, ReportTemplate
from sample.models.aliquot import Aliquot, AliquotLocation
from sample.models.sample import Sample
from sample.models.source import Source
from storage.models.site import Site
from storage.models.storage import Box, Device, Rack, Shelf

User = get_user_model()


class DashboardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='talia.hoang', password='x')
        self.client.force_login(self.user)
        site = Site.objects.create(name='Main')
        self.device = Device.objects.create(name='Sikora LN2', site=site)
        shelf = Shelf.objects.create(name='Canes', device=self.device)
        rack = Rack.objects.create(name='1', shelf=shelf)
        self.box = Box.objects.create(name='1_A', rack=rack, rows=2, columns=5)     # 10 slots
        self.sample = Sample.objects.create(name='MM134', source=Source.objects.create(name='Lab'))

    def store(self, count):
        aliquots = []
        for n in range(count):
            aliquot = Aliquot.objects.create(sample=self.sample)
            AliquotLocation.objects.create(aliquot=aliquot, box=self.box, row=n // 5 + 1, column=n % 5 + 1)
            aliquots.append(aliquot)
        return aliquots

    def page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        return response

    def test_fill_levels_use_the_agreed_thresholds(self):
        self.assertEqual([fill_level(p) for p in (0, 70, 71, 90, 91, 100)], ['ok', 'ok', 'warn', 'warn', 'full', 'full'])

    def test_freezer_card_shows_used_total_and_colour(self):
        self.store(8)                                    # 8 of 10 = 80%: amber
        card = self.page().context['freezers'][0]
        self.assertEqual((card['used'], card['total'], card['percent'], card['level']), (8, 10, 80, 'warn'))
        self.assertContains(self.page(), 'Sikora LN2')
        self.assertContains(self.page(), '8 of 10 slots')
        self.assertContains(self.page(), reverse('storage:detail', kwargs={'type': 'device', 'pk': self.device.pk}))

    def test_a_full_freezer_is_red_and_an_empty_one_says_so(self):
        self.assertEqual(self.page().context['freezers'][0]['last_activity'], 'Empty')
        self.store(10)
        card = self.page().context['freezers'][0]
        self.assertEqual((card['percent'], card['level']), (100, 'full'))
        self.assertEqual(card['last_activity'], 'Just now')

    def test_page_is_plain_and_does_not_blank_its_numbers_with_a_loading_script(self):
        self.store(3)
        page = self.page()
        self.assertNotContains(page, 'Welcome to Krill')
        self.assertNotContains(page, 'Laboratory Information Management System')
        self.assertNotContains(page, 'dashboard.js')       # it replaced every card with "Loading..."
        self.assertNotContains(page, 'storage slots used')  # the cards already say it
        self.assertEqual(page.context['stats']['aliquots'], 3)

    def test_site_name_only_appears_on_freezer_cards_when_there_are_several_sites(self):
        self.assertFalse(self.page().context['show_sites'])
        Device.objects.create(name='Other', site=Site.objects.create(name='Annex'))
        self.assertTrue(self.page().context['show_sites'])

    def test_quick_actions_drop_settings_and_offer_an_audit(self):
        page = self.page()
        self.assertNotContains(page, 'class="action-btn">\n                <span class="material-icons-round">settings')
        self.assertContains(page, reverse('reports:generate_audit_report'))

    def test_recent_activity_reads_as_a_sentence_with_where_it_is_stored(self):
        aliquot = self.store(1)[0]
        UserAuditLog.log_action(user=self.user, action='aliquot_created', target_type='Aliquot',
                                target_id=aliquot.id, target_name=str(aliquot))
        entry = self.page().context['recent_activity'][0]
        self.assertEqual(entry['user'], 'talia.hoang')
        self.assertEqual(entry['verb'], 'created aliquot')
        self.assertEqual(entry['place'], 'Sikora LN2 / Box 1_A')
        self.assertEqual(entry['url'], reverse('sample:detail', kwargs={'type': 'aliquot', 'pk': aliquot.id}))
        self.assertContains(self.page(), 'created aliquot')
        self.assertContains(self.page(), 'in Sikora LN2 / Box 1_A')

    def test_in_progress_audits_are_listed_until_finished(self):
        template = ReportTemplate.objects.create(name='t', report_type='storage_audit', created_by=self.user)
        slots = [{'result': 'correct'}, {'result': ''}]
        report = Report.objects.create(template=template, name='Spot check', status='complete', created_by=self.user,
                                       result_data={'audit_slots': slots})
        page = self.page()
        self.assertContains(page, 'Spot check')
        self.assertContains(page, '1 of 2 checked')
        slots[1]['result'] = 'wrong'
        report.result_data = {'audit_slots': slots}
        report.save()
        self.assertNotContains(self.page(), 'Spot check')

    def test_dashboard_still_loads_with_nothing_in_it(self):
        for model in (Box, Rack, Shelf, Device):       # children first: the foreign keys are PROTECT
            model.objects.all().delete()
        self.assertContains(self.page(), 'No freezers yet')
        self.assertContains(self.page(), 'No activity yet')
