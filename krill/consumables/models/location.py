from django.db import models
from django.utils import timezone


class ConsumableRoom(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ConsumableLocation(models.Model):
    LOCATION_KIND_CHOICES = [
        ('cabinet', 'Cabinet'),
        ('shelf', 'Shelf'),
        ('fridge', 'Refrigerator'),
        ('freezer', 'Freezer'),
        ('bench', 'Bench'),
        ('other', 'Other'),
    ]

    room = models.ForeignKey(
        ConsumableRoom,
        on_delete=models.PROTECT,
        related_name='locations',
    )
    name = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=20,
        choices=LOCATION_KIND_CHOICES,
        default='shelf',
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['room__name', 'name']
        indexes = [
            models.Index(fields=['room', 'name']),
        ]

    def __str__(self):
        return f"{self.room.name} / {self.name}"
