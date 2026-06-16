from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from consumables.models.consumable import Consumable
from consumables.models.consumable_type import ConsumableType
from consumables.models.location import ConsumableRoom, ConsumableLocation
from consumables.models.vendor import Vendor
from person.models import SiteConfiguration

User = get_user_model()


class ConsumablesViewBase(TestCase):
    def setUp(self):
        self.client = Client()
        # Enable consumables feature
        self.site_config = SiteConfiguration.load()
        self.site_config.consumables_enabled = True
        self.site_config.save()

        # Create users
        self.member = User.objects.create_user('member', 'member@example.com', 'pass')
        self.member.role.role = 'lab_member'
        self.member.role.save()

        self.manager = User.objects.create_user('manager', 'manager@example.com', 'pass')
        self.manager.role.role = 'lab_manager'
        self.manager.role.save()

        self.admin = User.objects.create_user('admin', 'admin@example.com', 'pass')
        self.admin.role.role = 'lab_admin'
        self.admin.role.save()

        self.viewer = User.objects.create_user('viewer', 'viewer@example.com', 'pass')
        self.viewer.role.role = 'viewer'
        self.viewer.role.save()

        # Common test data
        self.ctype = ConsumableType.objects.create(
            name='Antibody',
            category='antibody',
            spec_schema=[
                {'name': 'target', 'label': 'Target', 'type': 'text', 'required': True},
                {'name': 'host', 'label': 'Host Species', 'type': 'text', 'required': False},
            ],
        )
        self.vendor = Vendor.objects.create(name='Abcam')
        self.room = ConsumableRoom.objects.create(name='Cold Room')
        self.location = ConsumableLocation.objects.create(
            room=self.room, name='Shelf A', kind='shelf'
        )
        self.consumable = Consumable.objects.create(
            name='Anti-Mouse IgG',
            consumable_type=self.ctype,
            vendor=self.vendor,
            quantity=Decimal('5.0'),
            unit='vials',
            specs={'target': 'IgG', 'host': 'Rabbit'},
        )

    def tearDown(self):
        self.site_config.consumables_enabled = False
        self.site_config.save()


class FeatureToggleTest(ConsumablesViewBase):
    def test_list_returns_404_when_feature_disabled(self):
        self.site_config.consumables_enabled = False
        self.site_config.save()
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable')
        self.assertEqual(response.status_code, 404)

    def test_list_accessible_when_feature_enabled(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('consumables:list') + '?type=consumable')
        self.assertEqual(response.status_code, 302)


class ConsumablesListViewTest(ConsumablesViewBase):
    def test_list_shows_consumables(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anti-Mouse IgG')

    def test_list_search_filters(self):
        Consumable.objects.create(
            name='BSA',
            consumable_type=self.ctype,
            quantity=Decimal('1.0'),
            unit='g',
        )
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable&q=BSA')
        self.assertContains(response, 'BSA')
        self.assertNotContains(response, 'Anti-Mouse IgG')

    def test_list_excludes_deleted(self):
        self.consumable.deleted = True
        self.consumable.save()
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=consumable')
        self.assertNotContains(response, 'Anti-Mouse IgG')

    def test_list_types(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=type')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Antibody')

    def test_list_vendors(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=vendor')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abcam')

    def test_list_locations(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:list') + '?type=location')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shelf A')


class ConsumablesDetailViewTest(ConsumablesViewBase):
    def test_detail_shows_consumable(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(
            reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': self.consumable.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anti-Mouse IgG')

    def test_detail_shows_specs(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(
            reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': self.consumable.pk})
        )
        self.assertContains(response, 'IgG')

    def test_detail_vendor(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(
            reverse('consumables:detail', kwargs={'type': 'vendor', 'pk': self.vendor.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abcam')

    def test_detail_post_updates_consumable(self):
        self.client.login(username='member', password='pass')
        url = reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': self.consumable.pk})
        response = self.client.post(url, {
            'name': 'Anti-Mouse IgG Updated',
            'consumable_type': self.ctype.pk,
            'quantity': '4',
            'unit': 'vials',
            'spec__target': 'IgG',
        })
        self.assertEqual(response.status_code, 302)
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.name, 'Anti-Mouse IgG Updated')


class ConsumablesCreateViewTest(ConsumablesViewBase):
    def test_create_get_renders(self):
        self.client.login(username='member', password='pass')
        response = self.client.get(reverse('consumables:create') + '?type=consumable')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Consumable')

    def test_create_consumable(self):
        self.client.login(username='member', password='pass')
        response = self.client.post(
            reverse('consumables:create') + '?type=consumable',
            {
                'name': 'New Antibody',
                'consumable_type': self.ctype.pk,
                'quantity': '10',
                'unit': 'vials',
                'spec__target': 'p53',
                'spec__host': 'Mouse',
            }
        )
        self.assertEqual(response.status_code, 302)
        c = Consumable.objects.get(name='New Antibody')
        self.assertEqual(c.specs['target'], 'p53')
        self.assertEqual(c.specs['host'], 'Mouse')

    def test_create_vendor(self):
        self.client.login(username='member', password='pass')
        response = self.client.post(
            reverse('consumables:create') + '?type=vendor',
            {'name': 'Sigma Aldrich'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vendor.objects.filter(name='Sigma Aldrich').exists())

    def test_create_blocked_for_viewer(self):
        self.client.login(username='viewer', password='pass')
        response = self.client.post(
            reverse('consumables:create') + '?type=consumable',
            {'name': 'x', 'consumable_type': self.ctype.pk, 'quantity': '1', 'unit': 'vials'}
        )
        # viewer role does not meet lab_member minimum — should 403
        self.assertEqual(response.status_code, 403)


class ConsumablesDeleteViewTest(ConsumablesViewBase):
    def test_delete_soft_deletes(self):
        self.client.login(username='manager', password='pass')
        response = self.client.post(
            reverse('consumables:delete', kwargs={'pk': self.consumable.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.consumable.refresh_from_db()
        self.assertTrue(self.consumable.deleted)

    def test_delete_blocked_for_member(self):
        self.client.login(username='member', password='pass')
        response = self.client.post(
            reverse('consumables:delete', kwargs={'pk': self.consumable.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.consumable.refresh_from_db()
        self.assertFalse(self.consumable.deleted)


class ConsumablesAdjustViewTest(ConsumablesViewBase):
    def test_adjust_increases_quantity(self):
        self.client.login(username='member', password='pass')
        response = self.client.post(
            reverse('consumables:adjust', kwargs={'pk': self.consumable.pk}),
            {'delta': '3', 'note': 'received stock'}
        )
        self.assertEqual(response.status_code, 302)
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('8.0'))

    def test_adjust_decreases_quantity(self):
        self.client.login(username='member', password='pass')
        self.client.post(
            reverse('consumables:adjust', kwargs={'pk': self.consumable.pk}),
            {'delta': '-2', 'note': 'used in assay'}
        )
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('3.0'))

    def test_adjust_clamps_at_zero(self):
        self.client.login(username='member', password='pass')
        self.client.post(
            reverse('consumables:adjust', kwargs={'pk': self.consumable.pk}),
            {'delta': '-100'}
        )
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('0'))

    def test_adjust_blocked_for_viewer(self):
        self.client.login(username='viewer', password='pass')
        response = self.client.post(
            reverse('consumables:adjust', kwargs={'pk': self.consumable.pk}),
            {'delta': '1'}
        )
        self.assertEqual(response.status_code, 403)
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('5.0'))
