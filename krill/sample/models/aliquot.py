from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction
from storage.models import Box

class AliquotType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class AliquotDisposition(models.Model):
    DISPOSITION_CHOICES = [
        ('stored', 'Stored'),
        ('in_use', 'In Use'),
        ('exhausted', 'Exhausted'),
        ('disposed', 'Disposed'),
    ]
    name = models.CharField(max_length=100, unique=True)
    disposition_type = models.CharField(max_length=20, choices=DISPOSITION_CHOICES, default='stored')

    def __str__(self):
        return self.name

class Aliquot(models.Model):
    ACCESS_LEVEL_CHOICES = [
        ('admins_only', 'Admins Only'),
        ('admins_managers', 'Admins & Managers'),
        ('all_members', 'All Lab Members'),
    ]

    sample = models.ForeignKey('Sample', on_delete=models.CASCADE, related_name='aliquots')
    aliquot_type = models.ForeignKey(AliquotType, on_delete=models.PROTECT, null=True, blank=True)
    disposition = models.ForeignKey(AliquotDisposition, on_delete=models.PROTECT, null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='all_members',
        help_text="Restrict access to specific user tiers"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sample__name', 'id']

    def __str__(self):
        return f"{self.sample.name} - Aliquot {self.id}"

    def store_in_location(self, box, row, column):
        """Store this aliquot in a location"""
        stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        try:
            with transaction.atomic():
                if AliquotLocation.objects.filter(box=box, row=row, column=column).exists():
                    raise ValidationError(
                        f"Position ({row}, {column}) in box {box.name} is already occupied."
                    )
                # Remove existing location for this aliquot (allows moving)
                AliquotLocation.objects.filter(aliquot=self).delete()

                location = AliquotLocation.objects.create(
                    aliquot=self,
                    box=box,
                    row=row,
                    column=column,
                )
                self.disposition = stored_disposition
                self.save()
        except IntegrityError:
            if AliquotLocation.objects.filter(aliquot=self).exists():
                raise ValidationError(
                    "This aliquot already has a location. "
                    "This may be due to a concurrent assignment. Please try again."
                )
            raise ValidationError(
                f"Position ({row}, {column}) in box {box.name} is already occupied. "
                "Please try again with a different position."
            )
        return location


class AliquotLocation(models.Model):
    aliquot = models.OneToOneField(Aliquot, on_delete=models.CASCADE, related_name='location')
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    row = models.IntegerField()
    column = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['box', 'row', 'column']]

    def __str__(self):
        return f"{self.aliquot.sample.name} - Aliquot {self.aliquot.id} at {self.box.name} ({self.row},{self.column})"
