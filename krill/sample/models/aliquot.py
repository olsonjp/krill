from django.db import models
from django.utils import timezone
from storage.models import Box
from django.core.validators import MinValueValidator, MaxValueValidator

class AliquotType(models.Model):
    name = models.CharField(max_length=200, unique=True, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True, null=True)
    def __str__(self):
        return self.name

class AliquotDisposition(models.Model):
    TYPES = (
        ('stored', 'Stored'),
        ('exhausted', 'Exhausted'),
        ('in_use', 'In Use'),
    )
    name = models.CharField(max_length=200, unique=True, null=False, blank=False)
    dispositionType = models.CharField(max_length = 32, choices = TYPES, default = 'stored', null=False, blank=False)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Aliquot(models.Model):
    parent = models.ForeignKey(to='Aliquot', on_delete=models.PROTECT, null=True, blank=True)
    sample = models.ForeignKey(to='sample.Sample', on_delete=models.PROTECT, null=False, blank=False)
    quantity = models.IntegerField(default=0, null=False, blank=False, help_text="Number of test tubes in this aliquot")
    aliquotType = models.ForeignKey(to='AliquotType', on_delete=models.PROTECT, null=False, blank=False)
    # disposition is now computed from individual tubes
    passage = models.CharField(max_length=200, default=0)
    experiment = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.sample.name} - {self.aliquotType.name} - {self.quantity} tubes"

    @property
    def disposition(self):
        """
        Compute the aliquot disposition based on individual tube dispositions.
        - stored: if there is at least one stored tube
        - in_use: if there are no stored tubes and at least one in_use tube
        - exhausted: if all tubes are exhausted
        """
        stored_count = self.stored_tubes_count
        in_use_count = self.aliquottube_set.filter(disposition__dispositionType='in_use').count()
        exhausted_count = self.aliquottube_set.filter(disposition__dispositionType='exhausted').count()
        total_tubes = self.aliquottube_set.count()
        
        if stored_count > 0:
            return AliquotDisposition.objects.get(dispositionType='stored')
        elif in_use_count > 0:
            return AliquotDisposition.objects.get(dispositionType='in_use')
        elif exhausted_count == total_tubes:
            return AliquotDisposition.objects.get(dispositionType='exhausted')
        else:
            # Default fallback - should not happen in normal operation
            return AliquotDisposition.objects.get(dispositionType='stored')
    
    @property
    def stored_tubes_count(self):
        """Get the number of test tubes currently stored for this aliquot."""
        return self.aliquottube_set.filter(disposition__dispositionType='stored').count()
    
    @property
    def unstored_tubes_count(self):
        """Get the number of test tubes not yet stored for this aliquot."""
        return self.aliquottube_set.filter(disposition__dispositionType__in=['in_use', 'exhausted']).count()

class AliquotLocation(models.Model):
    aliquot = models.ForeignKey(to='Aliquot', on_delete=models.PROTECT, null=False, blank=False)
    box = models.ForeignKey(to='storage.Box', on_delete=models.PROTECT, null=False, blank=False)
    row = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)], null=False, blank=False)
    column = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)], null=False, blank=False)
    tube_number = models.PositiveSmallIntegerField(default=1, help_text="Tube number within this aliquot (1, 2, 3, etc.)")
    
    class Meta:
        unique_together = [
            ['aliquot', 'tube_number'],
            ['box', 'row', 'column']
        ]
    
    def __str__(self):
        return f"{self.aliquot.sample.name} - Tube {self.tube_number} at ({self.row}, {self.column})"

class AliquotTube(models.Model):
    """
    Represents an individual test tube within an aliquot.
    Each tube has its own disposition status and optional storage location.
    """
    aliquot = models.ForeignKey(to='Aliquot', on_delete=models.PROTECT, null=False, blank=False)
    tube_number = models.PositiveSmallIntegerField(help_text="Tube number within this aliquot (1, 2, 3, etc.)")
    disposition = models.ForeignKey(to='AliquotDisposition', on_delete=models.PROTECT, null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['aliquot', 'tube_number']
    
    def __str__(self):
        return f"{self.aliquot.sample.name} - Tube {self.tube_number} ({self.disposition.name})"
    
    @property
    def storage_location(self):
        """Get the storage location for this tube if it's stored."""
        if self.disposition.dispositionType == 'stored':
            try:
                return self.aliquotlocation_set.first()
            except:
                return None
        return None
    
