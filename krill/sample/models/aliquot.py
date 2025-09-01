from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
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
    quantity = models.IntegerField(default=1)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='all_members',
        help_text="Restrict access to specific user tiers"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.sample.name} - Aliquot {self.id}"

    @property
    def disposition(self):
        """Computed disposition based on individual tube dispositions"""
        if not hasattr(self, '_disposition_cache'):
            stored_tubes = self.tubes.filter(disposition__disposition_type='stored').count()
            total_tubes = self.tubes.count()
            
            if total_tubes == 0:
                self._disposition_cache = 'exhausted'
            elif stored_tubes == total_tubes:
                self._disposition_cache = 'stored'
            elif stored_tubes == 0:
                self._disposition_cache = 'exhausted'
            else:
                self._disposition_cache = 'in_use'
        return self._disposition_cache

    @property
    def stored_tubes_count(self):
        """Count of tubes with 'stored' disposition"""
        return self.tubes.filter(disposition__disposition_type='stored').count()

    @property
    def unstored_tubes_count(self):
        """Count of tubes that are not 'stored'"""
        return self.tubes.exclude(disposition__disposition_type='stored').count()
    
    @property
    def in_use_tubes_count(self):
        """Count of tubes with 'in_use' disposition"""
        return self.tubes.filter(disposition__disposition_type='in_use').count()
    
    @property
    def exhausted_tubes_count(self):
        """Count of tubes with 'exhausted' disposition"""
        return self.tubes.filter(disposition__disposition_type='exhausted').count()

    def create_tubes(self, auto_store=True):
        """Create individual tubes for this aliquot"""
        from .aliquot_tube import AliquotTube
        from .aliquot_disposition import AliquotDisposition
        
        # Get the default 'stored' disposition
        stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        
        # Create tubes
        for i in range(1, self.quantity + 1):
            AliquotTube.objects.create(
                aliquot=self,
                tube_number=i,
                disposition=stored_disposition
            )
        
        # Auto-store if enabled
        if auto_store:
            from sample.signals import auto_store_aliquot_tubes
            auto_store_aliquot_tubes(self)

    def change_tube_disposition(self, tube_number, disposition):
        """Change disposition of a specific tube"""
        try:
            tube = self.tubes.get(tube_number=tube_number)
            tube.disposition = disposition
            tube.save()
            # Clear disposition cache
            if hasattr(self, '_disposition_cache'):
                delattr(self, '_disposition_cache')
            return True
        except AliquotTube.DoesNotExist:
            raise ValidationError(f"Tube {tube_number} does not exist for this aliquot")

    def store_tube_in_location(self, tube_number, box, row, column):
        """Store a specific tube in a location"""
        from .aliquot_location import AliquotLocation
        
        # Change tube disposition to stored
        stored_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='Stored',
            defaults={'disposition_type': 'stored'}
        )
        self.change_tube_disposition(tube_number, stored_disposition)
        
        # Create or update location
        location, created = AliquotLocation.objects.get_or_create(
            aliquot=self,
            tube_number=tube_number,
            defaults={
                'box': box,
                'row': row,
                'column': column
            }
        )
        if not created:
            location.box = box
            location.row = row
            location.column = column
            location.save()
        return location

class AliquotTube(models.Model):
    aliquot = models.ForeignKey(Aliquot, on_delete=models.CASCADE, related_name='tubes')
    tube_number = models.IntegerField()
    disposition = models.ForeignKey(AliquotDisposition, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['aliquot', 'tube_number']

    def __str__(self):
        return f"{self.aliquot.sample.name} - Tube {self.tube_number}"

class AliquotLocation(models.Model):
    aliquot = models.ForeignKey(Aliquot, on_delete=models.CASCADE, related_name='locations')
    tube_number = models.IntegerField()
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    row = models.IntegerField()
    column = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['aliquot', 'tube_number'], ['box', 'row', 'column']]

    def __str__(self):
        return f"{self.aliquot.sample.name} - Tube {self.tube_number} at {self.box.name} ({self.row},{self.column})"
