from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from person.models import SiteConfiguration
from ..models.aliquot import Aliquot, AliquotDisposition
from .test_views import SampleViewTest

User = get_user_model()


class DashboardSectionsTest(SampleViewTest):
    """The dashboard groups its tiles under Samples, Storage and Consumables, like the sidebar."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.in_use = AliquotDisposition.objects.get_or_create(
            name='In Use', defaults={'disposition_type': 'in_use'})[0]

    def _html(self):
        return self.client.get(reverse('home')).content.decode()

    def _consumables(self, enabled):
        config = SiteConfiguration.load()
        config.consumables_enabled = enabled
        config.save()

    def _owned(self):
        return Aliquot.objects.create(
            sample=self.sample, disposition=self.in_use,
            checked_out_by=self.user, checked_out_at=timezone.now())

    def test_groups_appear_in_order_with_recent_activity_last(self):
        self._consumables(True)
        html = self._html()
        positions = [html.index(f'class="dashboard-group-label">{name}<') for name in ('Samples', 'Storage', 'Consumables')]
        self.assertEqual(positions, sorted(positions))
        self.assertGreater(html.index('<h2>Recent Activity</h2>'), positions[-1])

    def test_sample_tiles_and_checked_out_card_sit_in_the_samples_group(self):
        self._owned()
        html = self._html()
        start, end = html.index('>Samples<'), html.index('class="dashboard-group-label">Storage<')
        group = html[start:end]
        for expected in ('<h3>Samples</h3>', '<h3>Aliquots</h3>', 'Checked out by you (1)'):
            self.assertIn(expected, group)
        for elsewhere in ('<h3>Storage Used</h3>', '<h3>Audits</h3>', '<h2>Freezers</h2>'):
            self.assertNotIn(elsewhere, group)

    def test_storage_tiles_and_freezers_sit_in_the_storage_group(self):
        self._consumables(True)
        html = self._html()
        start = html.index('class="dashboard-group-label">Storage<')
        end = html.index('class="dashboard-group-label">Consumables<')
        group = html[start:end]
        for expected in ('<h3>Storage Used</h3>', '<h3>Audits</h3>', '<h2>Freezers</h2>'):
            self.assertIn(expected, group)

    def test_alerts_tile_is_kept_and_sits_after_audits_in_the_storage_group(self):
        self._consumables(True)
        html = self._html()
        group = html[html.index('class="dashboard-group-label">Storage<'):html.index('class="dashboard-group-label">Consumables<')]
        self.assertRegex(group, r'<div class="stat-info">\s*<h3>Alerts</h3>')
        self.assertLess(group.index('<h3>Audits</h3>'), group.index('<h3>Alerts</h3>'))
        self.assertIn(reverse('reports:alert_list'), group)

    def test_consumable_tiles_sit_in_the_consumables_group_when_enabled(self):
        self._consumables(True)
        html = self._html()
        group = html[html.index('class="dashboard-group-label">Consumables<'):html.index('<h2>Recent Activity</h2>')]
        self.assertIn('<h3>Low Stock</h3>', group)
        self.assertIn('<h3>Expiring Soon</h3>', group)

    def test_no_consumables_group_when_the_feature_is_off(self):
        self._consumables(False)
        html = self._html()
        self.assertNotIn('Consumables<', html.replace('class="dashboard-group-label">Samples<', ''))
        self.assertNotIn('<h3>Low Stock</h3>', html)
        self.assertNotIn('<h3>Expiring Soon</h3>', html)

    def test_quick_actions_come_before_the_groups(self):
        html = self._html()
        self.assertLess(html.index('class="quick-actions"'), html.index('class="dashboard-group-label">Samples<'))

    def test_manager_tile_is_in_the_samples_group(self):
        manager = User.objects.create_user(username='mgr', password='x')
        manager.role.role = 'lab_manager'
        manager.role.save()
        self.client.force_login(manager)
        html = self._html()
        group = html[html.index('>Samples<'):html.index('class="dashboard-group-label">Storage<')]
        self.assertIn('<h3>Lab Checkouts</h3>', group)
