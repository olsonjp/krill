from django.db import models
from django.utils import timezone


class ConsumableType(models.Model):
    CATEGORY_CHOICES = [
        ('antibody', 'Antibody'),
        ('enzyme', 'Enzyme'),
        ('kit', 'Kit'),
        ('chemical', 'Chemical/Reagent'),
        ('cell_line', 'Cell Line'),
        ('plasmid', 'Plasmid'),
        ('oligo', 'Oligo/Primer'),
        ('plasticware', 'Plasticware'),
        ('media', 'Media/Buffer'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
    )
    description = models.TextField(blank=True, null=True)
    # List of {name, label, type, required, choices?, help?}
    # type in: text | textarea | number | date | boolean | choice
    spec_schema = models.JSONField(default=list, blank=True)
    icon = models.CharField(max_length=50, default='category', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def css_class(self):
        return self.category.replace('_', '-')
