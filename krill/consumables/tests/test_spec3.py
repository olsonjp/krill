from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from consumables.models.consumable import Consumable
from consumables.models.consumable_type import ConsumableType
from consumables.models.vendor import Vendor
from person.models import SiteConfiguration

User = get_user_model()


class Spec3Base(TestCase):
    def setUp(self):
        self.client = Client()
        self.config = SiteConfiguration.load()
        self.config.consumables_enabled = True
        self.config.consumables_ordering_enabled = True
        self.config.save()

        self.member = User.objects.create_user('s3member', 's3@example.com', 'pass')
        self.member.role.role = 'lab_member'
        self.member.role.save()

        self.ctype = ConsumableType.objects.create(name='Enzyme', category='enzyme')
        self.vendor = Vendor.objects.create(name='NEB')

        # Low stock item
        self.low = Consumable.objects.create(
            name='EcoRI',
            consumable_type=self.ctype,
            vendor=self.vendor,
            catalog_number='R0101S',
            quantity=Decimal('2'),
            unit='vials',
            low_stock_threshold=Decimal('5'),
        )
        # Well-stocked item
        self.ok = Consumable.objects.create(
            name='BamHI',
            consumable_type=self.ctype,
            quantity=Decimal('20'),
            unit='vials',
            low_stock_threshold=Decimal('5'),
        )
        # Expiring soon item
        self.expiring = Consumable.objects.create(
            name='T4 Ligase',
            consumable_type=self.ctype,
            quantity=Decimal('10'),
            unit='vials',
            expiration_date=date.today() + timedelta(days=15),
        )
        # Already expired (should NOT appear in expiring-soon)
        self.expired = Consumable.objects.create(
            name='Old Buffer',
            consumable_type=self.ctype,
            quantity=Decimal('5'),
            unit='bottles',
            expiration_date=date.today() - timedelta(days=1),
        )

    def tearDown(self):
        self.config.consumables_enabled = False
        self.config.consumables_ordering_enabled = False
        self.config.save()


class DashboardStatsTest(Spec3Base):
    def test_low_stock_count_in_stats(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['low_stock_count'], 1)

    def test_expiring_soon_count_in_stats(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['stats']['expiring_soon_count'], 1)

    def test_low_stock_zero_when_feature_disabled(self):
        self.config.consumables_enabled = False
        self.config.save()
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['stats']['low_stock_count'], 0)
        self.assertEqual(response.context['stats']['expiring_soon_count'], 0)


class ListFilterTest(Spec3Base):
    def test_low_stock_filter_shows_only_low_stock(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable&low_stock=1')
        self.assertEqual(response.status_code, 200)
        names = [c.name for c in response.context['items']]
        self.assertIn('EcoRI', names)
        self.assertNotIn('BamHI', names)

    def test_expiring_filter_shows_only_expiring_soon(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable&expiring=1')
        names = [c.name for c in response.context['items']]
        self.assertIn('T4 Ligase', names)
        self.assertNotIn('Old Buffer', names)
        self.assertNotIn('EcoRI', names)

    def test_filter_context_flags(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable&low_stock=1')
        self.assertTrue(response.context['filter_low_stock'])
        self.assertFalse(response.context['filter_expiring'])


class ReorderListTest(Spec3Base):
    def test_reorder_list_returns_200(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:reorder_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoRI')
        self.assertNotContains(response, 'BamHI')

    def test_reorder_list_404_when_ordering_disabled(self):
        self.config.consumables_ordering_enabled = False
        self.config.save()
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:reorder_list'))
        self.assertEqual(response.status_code, 404)

    def test_reorder_csv_returns_csv(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:reorder_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode()
        self.assertIn('EcoRI', content)
        self.assertIn('R0101S', content)
        self.assertNotIn('BamHI', content)

    def test_reorder_csv_headers(self):
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:reorder_csv'))
        first_line = response.content.decode().splitlines()[0]
        self.assertIn('Catalog #', first_line)
        self.assertIn('Vendor', first_line)

    def test_reorder_csv_404_when_ordering_disabled(self):
        self.config.consumables_ordering_enabled = False
        self.config.save()
        self.client.login(username='s3member', password='pass')
        response = self.client.get(reverse('consumables:reorder_csv'))
        self.assertEqual(response.status_code, 404)
