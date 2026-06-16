from django.db import models
from django.utils import timezone


class Vendor(models.Model):
    name = models.CharField(max_length=200, unique=True)
    website = models.URLField(blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
