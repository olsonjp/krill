from django.db import models
from django.db.models import Count, Q
from storage.models import Box


class SampleQuerySet(models.QuerySet):
    def with_stored_count(self):
        """Add stored_count (aliquots whose disposition is Stored) and aliquot_total (all aliquots).

        Soft-deleted aliquots are left out of both. A box position is not required: many stored
        aliquots have not been given one.
        """
        return self.annotate(
            stored_count=Count(
                'aliquots',
                filter=Q(aliquots__deleted=False, aliquots__disposition__disposition_type='stored'),
            ),
            aliquot_total=Count('aliquots', filter=Q(aliquots__deleted=False)),
        )


class Sample(models.Model):
    ACCESS_LEVEL_CHOICES = [
        ('admins_only', 'Admins Only'),
        ('admins_managers', 'Admins & Managers'),
        ('all_members', 'All Lab Members'),
    ]

    name = models.CharField(max_length=200, db_index=True)
    experiment = models.TextField(blank=True, null=True)
    source = models.ForeignKey(to='Source', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='all_members',
        help_text="Restrict access to specific user tiers"
    )

    low_count_check = models.BooleanField(
        default=True,
        help_text='Warn when few stored aliquots are left. Turn off for a sample that is deliberately kept low.',
    )
    low_count_warn = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Warn at this many stored aliquots or fewer. Leave blank to use the lab default.',
    )
    low_count_alert = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Alert at this many stored aliquots or fewer. Leave blank to use the lab default.',
    )

    objects = SampleQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
