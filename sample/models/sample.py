from django.db import models
from storage.models import Box

class Sample(models.Model):
    ACCESS_LEVEL_CHOICES = [
        ('admins_only', 'Admins Only'),
        ('admins_managers', 'Admins & Managers'),
        ('all_members', 'All Lab Members'),
    ]

    name = models.CharField(max_length=200)
    experiment = models.TextField(blank=True, null=True)
    source = models.ForeignKey(to='Source', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='all_members',
        help_text="Restrict access to specific user tiers"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
