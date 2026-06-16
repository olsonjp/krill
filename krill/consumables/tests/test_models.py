from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from consumables.models.consumable_type import ConsumableType
from consumables.models.consumable import Consumable
from consumables.models.vendor import Vendor
from consumables.models.location import ConsumableRoom, ConsumableLocation


class ConsumableModelTest(TestCase):
    def setUp(self):
        self.ctype = ConsumableType.objects.create(
            name='Antibody',
            category='antibody',
            spec_schema=[{'name': 'target', 'label': 'Target', 'type': 'text', 'required': True}],
        )
        self.vendor = Vendor.objects.create(name='Test Vendor')
        self.room = ConsumableRoom.objects.create(name='Cold Room')
        self.location = ConsumableLocation.objects.create(
            room=self.room,
            name='Shelf A',
            kind='shelf',
        )

    def _make_consumable(self, **kwargs):
        defaults = dict(
            name='Anti-Mouse IgG',
            consumable_type=self.ctype,
            quantity=Decimal('5.000'),
            unit='vials',
        )
        defaults.update(kwargs)
        return Consumable.objects.create(**defaults)

    def test_str(self):
        c = self._make_consumable()
        self.assertEqual(str(c), 'Anti-Mouse IgG')

    def test_is_low_stock_true(self):
        c = self._make_consumable(quantity=Decimal('2'), low_stock_threshold=Decimal('3'))
        self.assertTrue(c.is_low_stock)

    def test_is_low_stock_at_threshold(self):
        c = self._make_consumable(quantity=Decimal('3'), low_stock_threshold=Decimal('3'))
        self.assertTrue(c.is_low_stock)

    def test_is_low_stock_false(self):
        c = self._make_consumable(quantity=Decimal('5'), low_stock_threshold=Decimal('3'))
        self.assertFalse(c.is_low_stock)

    def test_is_low_stock_no_threshold(self):
        c = self._make_consumable(quantity=Decimal('1'), low_stock_threshold=None)
        self.assertFalse(c.is_low_stock)

    def test_is_out_of_stock(self):
        c = self._make_consumable(quantity=Decimal('0'))
        self.assertTrue(c.is_out_of_stock)

    def test_is_not_out_of_stock(self):
        c = self._make_consumable(quantity=Decimal('1'))
        self.assertFalse(c.is_out_of_stock)

    def test_is_expired(self):
        yesterday = date.today() - timedelta(days=1)
        c = self._make_consumable(expiration_date=yesterday)
        self.assertTrue(c.is_expired)

    def test_is_not_expired_future(self):
        tomorrow = date.today() + timedelta(days=1)
        c = self._make_consumable(expiration_date=tomorrow)
        self.assertFalse(c.is_expired)

    def test_is_not_expired_no_date(self):
        c = self._make_consumable(expiration_date=None)
        self.assertFalse(c.is_expired)

    def test_active_excludes_deleted(self):
        c = self._make_consumable()
        self.assertEqual(Consumable.objects.active().count(), 1)
        c.deleted = True
        c.deleted_at = timezone.now()
        c.save()
        self.assertEqual(Consumable.objects.active().count(), 0)

    def test_low_stock_queryset(self):
        self._make_consumable(name='Low', quantity=Decimal('1'), low_stock_threshold=Decimal('5'))
        self._make_consumable(name='OK', quantity=Decimal('10'), low_stock_threshold=Decimal('5'))
        self._make_consumable(name='No threshold', quantity=Decimal('1'))
        qs = Consumable.objects.low_stock()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().name, 'Low')

    def test_low_stock_queryset_excludes_deleted(self):
        c = self._make_consumable(quantity=Decimal('1'), low_stock_threshold=Decimal('5'))
        c.deleted = True
        c.deleted_at = timezone.now()
        c.save()
        self.assertEqual(Consumable.objects.low_stock().count(), 0)

    def test_specs_stored_as_dict(self):
        c = self._make_consumable(specs={'target': 'CD3', 'host': 'Mouse'})
        c.refresh_from_db()
        self.assertEqual(c.specs['target'], 'CD3')
        self.assertEqual(c.specs['host'], 'Mouse')


class ConsumableTypeModelTest(TestCase):
    def test_css_class(self):
        ct = ConsumableType(category='cell_line')
        self.assertEqual(ct.css_class, 'cell-line')

    def test_str(self):
        ct = ConsumableType(name='Antibody')
        self.assertEqual(str(ct), 'Antibody')


class ConsumableLocationModelTest(TestCase):
    def test_str(self):
        room = ConsumableRoom(name='Lab 2')
        loc = ConsumableLocation(room=room, name='Cabinet B')
        self.assertEqual(str(loc), 'Lab 2 / Cabinet B')

    def test_vendor_str(self):
        v = Vendor(name='Thermo Fisher')
        self.assertEqual(str(v), 'Thermo Fisher')
