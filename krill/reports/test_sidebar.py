import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

REPORT_PAGES = {
    'Overview': 'reports:reports_dashboard',
    'Storage Audits': 'reports:audit_list',
    'Alerts': 'reports:alert_list',
    'Checked Out, No Owner': 'reports:checked_out_no_owner',
}


class ReportsSidebarSectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', password='x')
        self.client.force_login(self.user)

    def _item_classes(self, html, url):
        match = re.search(r'<a href="%s" class="(submenu-item[^"]*)"' % re.escape(url), html)
        self.assertIsNotNone(match, f'sidebar has no submenu item for {url}')
        return match.group(1)

    def test_every_report_page_is_reachable_from_the_sidebar_on_any_page(self):
        for page in ('home', 'sample:sample_list', 'settings'):
            html = self.client.get(reverse(page)).content.decode()
            section = html[html.index('id="reports-section"'):]
            for label, name in REPORT_PAGES.items():
                with self.subTest(page=page, item=label):
                    self.assertIn(f'href="{reverse(name)}"', section)
                    self.assertIn(f'<h3>{label}</h3>', section)

    def test_section_is_collapsed_away_from_reports_and_open_inside_it(self):
        away = self.client.get(reverse('home')).content.decode()
        self.assertIn('id="reports-section" class="sidebar-submenu "', away)
        inside = self.client.get(reverse('reports:alert_list')).content.decode()
        self.assertIn('id="reports-section" class="sidebar-submenu show"', inside)

    def test_the_current_page_is_the_active_item(self):
        for label, name in REPORT_PAGES.items():
            with self.subTest(label=label):
                html = self.client.get(reverse(name)).content.decode()
                for other_label, other_name in REPORT_PAGES.items():
                    classes = self._item_classes(html, reverse(other_name))
                    if other_name == name:
                        self.assertIn('active', classes.split(), f'{other_label} should be active on {label}')
                    else:
                        self.assertNotIn('active', classes.split(), f'{other_label} should not be active on {label}')

    def test_audit_detail_pages_keep_storage_audits_active(self):
        url = reverse('reports:generate_audit_report')
        html = self.client.get(url).content.decode()
        self.assertIn('active', self._item_classes(html, reverse('reports:audit_list')).split())
