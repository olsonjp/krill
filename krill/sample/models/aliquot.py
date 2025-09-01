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
        if total_tubes == 0:
            # No tubes - exhausted
            return AliquotDisposition.objects.get(dispositionType='exhausted')
        elif stored_count > 0:
            return AliquotDisposition.objects.get(dispositionType='stored')
        elif in_use_count > 0:
            return AliquotDisposition.objects.get(dispositionType='in_use')
        elif exhausted_count == total_tubes:
            return AliquotDisposition.objects.get(dispositionType='exhausted')
        else:
            # Default fallback - should not happen in normal operation
            return AliquotDisposition.objects.get(dispositionType='stored')
    def create_tubes(self, quantity=None, auto_store=True):
        """
        Explicitly create tubes for this aliquot.
        Args:
            quantity: Number of tubes to create (defaults to self.quantity)
            auto_store: Whether to automatically store tubes in available locations
        """
        if quantity is None:
            quantity = self.quantity
        # Get the default disposition
        default_disposition = AliquotDisposition.objects.get(dispositionType='stored')
        # Create individual tube instances
        for tube_number in range(1, quantity + 1):
            tube = AliquotTube.objects.create(
                aliquot=self,
                tube_number=tube_number,
                disposition=default_disposition
            )
            # Auto-store if requested
            if auto_store:
                self._auto_store_tube(tube)
    def _auto_store_tube(self, tube):
        """
        Automatically store a tube in an available location.
        """
        from storage.models import Box
        # Only auto-store if disposition is "Stored"
        if tube.disposition.dispositionType != 'stored':
            return
        # Check if tube already has a storage location
        if AliquotLocation.objects.filter(aliquot=self, tube_number=tube.tube_number).exists():
            return
        # Find available auto-store boxes
        auto_store_boxes = Box.objects.filter(
            rack__shelf__device__auto_store_enabled=True
        ).order_by('id')
        for box in auto_store_boxes:
            available_slots = box.get_available_slots()
            if available_slots:
                # Store tube in first available slot
                slot = available_slots[0]
                AliquotLocation.objects.create(
                    aliquot=self,
                    box=box,
                    row=slot['row'],
                    column=slot['column'],
                    tube_number=tube.tube_number
                )
                break
    def store_tube_in_location(self, tube_number, box, row, column):
        """
        Store a specific tube in a specific location.
        Args:
            tube_number: The tube number to store
            box: The box to store it in
            row: The row coordinate
            column: The column coordinate
        """
        # Check if tube exists
        if not AliquotTube.objects.filter(aliquot=self, tube_number=tube_number).exists():
            raise ValueError(f"Tube {tube_number} does not exist for this aliquot")
        # Remove any existing location for this tube
        AliquotLocation.objects.filter(aliquot=self, tube_number=tube_number).delete()
        # Create new location
        AliquotLocation.objects.create(
            aliquot=self,
            box=box,
            row=row,
            column=column,
            tube_number=tube_number
        )
    def change_tube_disposition(self, tube_number, new_disposition):
        """
        Change the disposition of a specific tube.
        Args:
            tube_number: The tube number to change
            new_disposition: The new disposition object
        """
        try:
            tube = AliquotTube.objects.get(aliquot=self, tube_number=tube_number)
            tube.disposition = new_disposition
            tube.save()
            # If changing from stored to non-stored, remove storage location
            if new_disposition.dispositionType != 'stored':
                AliquotLocation.objects.filter(aliquot=self, tube_number=tube_number).delete()
        except AliquotTube.DoesNotExist:
            raise ValueError(f"Tube {tube_number} does not exist for this aliquot")
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
