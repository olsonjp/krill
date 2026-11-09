from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


class SupportLinksTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username='root', password='x', email='r@example.com')
        self.client.force_login(self.user)

    def test_sidebar_has_a_support_link_above_logout(self):
        body = self.client.get(reverse('storage:storage')).content.decode()
        link = 'href="mailto:support@krillbio.com?subject=Krill%20support%20request"'
        self.assertIn(link, body)
        self.assertIn('<h3>Support</h3>', body)
        self.assertLess(body.index(link), body.index('<h3>Logout</h3>'))

    def test_report_issue_button_emails_support(self):
        body = self.client.get(reverse('storage:storage')).content.decode()
        self.assertIn('href="mailto:support@krillbio.com?subject=Krill%20issue%20report" class="action-btn"', body)
        self.assertNotIn(f'href="{reverse("reports:alert_list")}" class="action-btn"', body)

    def test_support_link_is_on_other_pages_too(self):
        body = self.client.get(reverse('home')).content.decode()
        self.assertIn('mailto:support@krillbio.com', body)

    @override_settings(SUPPORT_EMAIL='help@example.org')
    def test_address_comes_from_settings(self):
        body = self.client.get(reverse('storage:storage')).content.decode()
        self.assertIn('mailto:help@example.org?subject=Krill%20issue%20report', body)
        self.assertNotIn('support@krillbio.com', body)

    def test_alerts_remain_reachable_from_the_home_page(self):
        body = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('reports:alert_list'), body)
