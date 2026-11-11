from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from consumables.models.consumable import Consumable
from consumables.models.consumable_type import ConsumableType
from person.models import SiteConfiguration, UserAuditLog
from reports import attention

User = get_user_model()


class AttentionFixture(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', password='x')
        self.manager = User.objects.create_user(username='mgr', password='x')
        self.manager.role.role = 'lab_manager'
        self.manager.role.save()
        self.kind = ConsumableType.objects.create(name='Antibody', category='antibody')
        self.set_consumables(True)

    def set_consumables(self, enabled):
        config = SiteConfiguration.load()
        config.consumables_enabled = enabled
        config.save()

    def consumable(self, name='Anti-GFP', quantity='3', threshold='5', expires=None, **kwargs):
        return Consumable.objects.create(
            name=name, consumable_type=self.kind, quantity=Decimal(quantity),
            low_stock_threshold=None if threshold is None else Decimal(threshold),
            expiration_date=expires, **kwargs)


class LowStockSourceTest(AttentionFixture):
    def test_item_has_stable_key_text_level_and_link(self):
        c = self.consumable(quantity='3', threshold='5')
        [item] = attention.low_stock_items()
        self.assertEqual(item.key, f'low_stock:consumable:{c.pk}')
        self.assertEqual(item.title, 'Anti-GFP')
        self.assertEqual(item.detail, '3 units left (reorder at 5)')
        self.assertEqual(item.level, 'warn')
        self.assertEqual(item.url, reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': c.pk}))
        self.assertEqual((item.target_type, item.target_id, item.silenced), ('consumable', c.pk, False))

    def test_out_of_stock_is_an_alert(self):
        self.consumable(quantity='0', threshold='5')
        [item] = attention.low_stock_items()
        self.assertEqual(item.level, 'alert')
        self.assertIn('Out of stock', item.detail)

    def test_at_the_threshold_counts_and_above_does_not(self):
        self.consumable('At', quantity='5', threshold='5')
        self.consumable('Above', quantity='6', threshold='5')
        self.consumable('No threshold', quantity='0', threshold=None)
        self.assertEqual([i.title for i in attention.low_stock_items()], ['At'])

    def test_deleted_consumables_are_ignored(self):
        self.consumable(deleted=True)
        self.assertEqual(attention.low_stock_items(), [])

    def test_silenced_items_are_returned_but_marked(self):
        self.consumable(alerts_silenced=True)
        [item] = attention.low_stock_items()
        self.assertTrue(item.silenced)


class ExpiringSourceTest(AttentionFixture):
    def test_item_text_and_level(self):
        soon = date.today() + timedelta(days=10)
        c = self.consumable(threshold=None, expires=soon)
        [item] = attention.expiring_items()
        self.assertEqual(item.key, f'expiring:consumable:{c.pk}')
        self.assertEqual(item.detail, f'Expires {soon:%Y-%m-%d} (in 10 days)')
        self.assertEqual(item.level, 'warn')

    def test_today_and_singular_wording(self):
        self.consumable('Today', threshold=None, expires=date.today())
        self.consumable('Tomorrow', threshold=None, expires=date.today() + timedelta(days=1))
        details = {i.title: i.detail for i in attention.expiring_items()}
        self.assertTrue(details['Today'].endswith('(today)'))
        self.assertTrue(details['Tomorrow'].endswith('(in 1 day)'))

    def test_window_is_today_to_30_days_like_the_dashboard_tile(self):
        self.consumable('Past', threshold=None, expires=date.today() - timedelta(days=1))
        self.consumable('Edge', threshold=None, expires=date.today() + timedelta(days=30))
        self.consumable('Far', threshold=None, expires=date.today() + timedelta(days=31))
        self.consumable('None', threshold=None, expires=None)
        self.assertEqual([i.title for i in attention.expiring_items()], ['Edge'])


class GroupsAndSummaryTest(AttentionFixture):
    def test_groups_split_active_from_silenced(self):
        self.consumable('Live', quantity='1', threshold='5')
        self.consumable('Quiet', quantity='1', threshold='5', alerts_silenced=True)
        low = next(g for g in attention.groups() if g['source'].name == 'low_stock')
        self.assertEqual([i.title for i in low['active']], ['Live'])
        self.assertEqual([i.title for i in low['silenced']], ['Quiet'])

    def test_summary_counts_only_unsilenced_items_across_sources(self):
        self.consumable('A', quantity='1', threshold='5', expires=date.today() + timedelta(days=3))
        self.consumable('B', quantity='1', threshold='5', alerts_silenced=True,
                        expires=date.today() + timedelta(days=3))
        # A is low stock and expiring: two items; B is silenced for both
        self.assertEqual(attention.summary(), {'count': 2, 'level': 'warn'})

    def test_worst_level_wins(self):
        self.consumable('Empty', quantity='0', threshold='5')
        self.consumable('Low', quantity='1', threshold='5')
        self.assertEqual(attention.summary()['level'], 'alert')

    def test_all_clear(self):
        self.assertEqual(attention.summary(), {'count': 0, 'level': None})

    def test_consumable_sources_are_hidden_when_the_feature_is_off(self):
        self.consumable(quantity='0', threshold='5')
        self.set_consumables(False)
        # Only the sources that do not depend on Consumables remain
        self.assertEqual([g['source'].name for g in attention.groups()], ['low_count'])
        self.assertEqual(attention.summary(), {'count': 0, 'level': None})

    def test_no_groups_at_all_when_no_source_is_available(self):
        from unittest.mock import patch
        with patch.object(attention, 'SOURCES', []):
            self.assertEqual(attention.groups(), [])
            self.assertEqual(attention.summary(), {'count': 0, 'level': None})


class SilenceTest(AttentionFixture):
    def test_silence_and_unsilence_a_consumable(self):
        c = self.consumable()
        self.assertTrue(attention.silence('consumable', c.pk, True))
        c.refresh_from_db()
        self.assertTrue(c.alerts_silenced)
        self.assertTrue(attention.silence('consumable', c.pk, False))
        c.refresh_from_db()
        self.assertFalse(c.alerts_silenced)

    def test_unknown_type_or_missing_record_changes_nothing(self):
        self.assertFalse(attention.silence('nonsense', 1, True))
        self.assertFalse(attention.silence('consumable', 99999, True))

    def test_silenced_consumable_leaves_low_stock_reorder_and_tile_filters(self):
        quiet = self.consumable('Quiet', alerts_silenced=True)
        loud = self.consumable('Loud')
        self.assertEqual(list(Consumable.objects.low_stock()), [loud])
        self.client.force_login(self.user)
        listed = self.client.get(reverse('consumables:list'), {'type': 'consumable', 'low_stock': '1'})
        self.assertEqual([c.pk for c in listed.context['items']], [loud.pk])
        self.assertNotIn(quiet.pk, [c.pk for c in listed.context['items']])


class OverviewPageTest(AttentionFixture):
    def setUp(self):
        super().setUp()
        self.url = reverse('reports:alert_list')

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_lists_items_by_source_with_levels_and_links(self):
        c = self.consumable('Anti-GFP', quantity='0', threshold='5', expires=date.today() + timedelta(days=5))
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total'], 2)
        self.assertEqual(response.context['level'], 'alert')
        self.assertContains(response, 'Low stock (1)')
        self.assertContains(response, 'Expiring soon (1)')
        self.assertContains(response, 'Out of stock')
        self.assertContains(response, reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': c.pk}))
        self.assertContains(response, '2 items need attention')

    def test_all_clear_and_empty_groups(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'All clear')
        self.assertContains(response, 'Nothing needs attention.')

    def test_explains_when_nothing_is_watched(self):
        from unittest.mock import patch
        self.client.force_login(self.user)
        with patch.object(attention, 'SOURCES', []):
            self.assertContains(self.client.get(self.url), 'Nothing is being watched yet.')

    def test_consumable_groups_are_absent_when_the_feature_is_off(self):
        self.set_consumables(False)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'Low sample counts (0)')
        self.assertNotContains(response, 'Low stock (')
        self.assertNotContains(response, 'Expiring soon (')

    def test_silenced_items_are_displayed_separately(self):
        self.consumable('Quiet', alerts_silenced=True)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['silenced_total'], 1)
        self.assertContains(response, 'Silenced (1)')
        self.assertContains(response, 'Quiet')
        self.assertContains(response, 'All clear')  # silenced items do not count

    def test_only_managers_get_silence_buttons(self):
        self.consumable('Live')
        self.consumable('Quiet', alerts_silenced=True)
        self.client.force_login(self.user)
        member = self.client.get(self.url)
        self.assertFalse(member.context['can_silence'])
        self.assertNotContains(member, 'name="silenced"')
        self.client.force_login(self.manager)
        manager = self.client.get(self.url)
        self.assertTrue(manager.context['can_silence'])
        self.assertContains(manager, 'name="silenced" value="1"')
        self.assertContains(manager, 'name="silenced" value="0"')
        self.assertContains(manager, 'Turn back on')

    def test_silence_uses_the_confirm_dialog_markup(self):
        self.consumable('Live')
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertContains(response, 'data-confirm="Silence alerts for Live?')
        self.assertContains(response, 'data-confirm-label="Silence"')

    def test_manual_alert_creation_is_gone(self):
        from django.urls import NoReverseMatch
        self.client.force_login(self.manager)
        self.assertNotContains(self.client.get(self.url), 'Create Alert')
        for name, args in (('create_alert', []), ('acknowledge_alert', [1]),
                           ('resolve_alert', [1]), ('alert_list_cbv', [])):
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse(f'reports:{name}', args=args)


class SilenceEndpointTest(AttentionFixture):
    def setUp(self):
        super().setUp()
        self.url = reverse('reports:silence_attention')
        self.c = self.consumable()

    def _post(self, silenced='1', **extra):
        return self.client.post(self.url, {'target_type': 'consumable', 'target_id': self.c.pk,
                                           'silenced': silenced, **extra})

    def test_manager_silences_and_it_is_logged(self):
        self.client.force_login(self.manager)
        response = self._post('1')
        self.assertRedirects(response, reverse('reports:alert_list'), fetch_redirect_response=False)
        self.c.refresh_from_db()
        self.assertTrue(self.c.alerts_silenced)
        self.assertTrue(UserAuditLog.objects.filter(action='alerts_silenced', user=self.manager).exists())
        self.assertContains(self.client.get(reverse('reports:alert_list')), 'Alerts silenced.')

    def test_manager_turns_alerts_back_on(self):
        self.c.alerts_silenced = True
        self.c.save()
        self.client.force_login(self.manager)
        self._post('0')
        self.c.refresh_from_db()
        self.assertFalse(self.c.alerts_silenced)
        self.assertTrue(UserAuditLog.objects.filter(action='alerts_unsilenced').exists())

    def test_member_is_refused(self):
        self.client.force_login(self.user)
        self.assertEqual(self._post('1').status_code, 403)
        self.c.refresh_from_db()
        self.assertFalse(self.c.alerts_silenced)

    def test_get_is_not_allowed_and_login_required(self):
        self.assertEqual(self.client.post(self.url, {}).status_code, 302)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_bad_input_changes_nothing_and_says_so(self):
        self.client.force_login(self.manager)
        for data in ({'target_type': 'nonsense', 'target_id': self.c.pk, 'silenced': '1'},
                     {'target_type': 'consumable', 'target_id': 'abc', 'silenced': '1'},
                     {'target_type': 'consumable', 'target_id': 99999, 'silenced': '1'}):
            with self.subTest(data=data):
                self.client.post(self.url, data)
                self.c.refresh_from_db()
                self.assertFalse(self.c.alerts_silenced)
        self.assertContains(self.client.get(reverse('reports:alert_list')), 'That item could not be found.')


class ReportsPageTileTest(AttentionFixture):
    def test_reports_page_shows_the_needs_attention_count(self):
        self.consumable(quantity='1', threshold='5')
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:reports_dashboard'))
        self.assertEqual(response.context['attention'], {'count': 1, 'level': 'warn'})
        self.assertContains(response, 'Needs Attention')
        self.assertNotContains(response, 'Recent Alerts')
        self.assertNotContains(response, 'Active Alerts')

    def test_stats_api_alerts_key_is_the_attention_count(self):
        self.consumable(quantity='1', threshold='5')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('reports:dashboard_stats')).json()['alerts'], 1)
