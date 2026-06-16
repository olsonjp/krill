from django.db import models
from django.db.models import F
from django.utils import timezone

from .consumable_type import ConsumableType
from .location import ConsumableLocation
from .vendor import Vendor


class ConsumableQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted=False)

    def low_stock(self):
        return self.active().filter(
            low_stock_threshold__isnull=False,
            quantity__lte=F('low_stock_threshold'),
        )


class Consumable(models.Model):
    ACCESS_LEVEL_CHOICES = [
        ('admins_only', 'Admins Only'),
        ('admins_managers', 'Admins & Managers'),
        ('all_members', 'All Lab Members'),
    ]

    name = models.CharField(max_length=255)
    consumable_type = models.ForeignKey(
        ConsumableType,
        on_delete=models.PROTECT,
        related_name='consumables',
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='consumables',
    )
    location = models.ForeignKey(
        ConsumableLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumables',
    )
    catalog_number = models.CharField(max_length=120, blank=True, null=True)
    lot_number = models.CharField(max_length=120, blank=True, null=True)

    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit = models.CharField(max_length=30, default='units')
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    specs = models.JSONField(default=dict, blank=True)

    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='all_members',
        help_text="Restrict access to specific user tiers",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ConsumableQuerySet.as_manager()

    class Meta:
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['consumable_type']),
            models.Index(fields=['location']),
            models.Index(fields=['deleted', 'name']),
            models.Index(fields=['catalog_number']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return (
            self.low_stock_threshold is not None
            and self.quantity <= self.low_stock_threshold
        )

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def is_expired(self):
        return (
            self.expiration_date is not None
            and self.expiration_date < timezone.now().date()
        )
