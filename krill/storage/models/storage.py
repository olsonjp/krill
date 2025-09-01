from django.db import models
from .site import Site

class Device(models.Model):
    """
    A Device represents a freezer or dewer in which Samples are stored.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='devices')
    auto_store_enabled = models.BooleanField(
        default=False, 
        help_text="Enable auto-store for all boxes in this device"
    )
    def __str__(self):
        return self.name

class Shelf(models.Model):
    """
    A Shelf represents a shelf in a freezer in which Samples are stored. Dewers will have a single shelf.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='shelves')

    class Meta:
        verbose_name_plural = "shelves"

    def __str__(self):
        return self.name

class Rack(models.Model):
    """
    A Rack represents a rack in a freezer or a cane in a dewer in which Samples are stored.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    shelf = models.ForeignKey(Shelf, on_delete=models.PROTECT, related_name='racks')

    def __str__(self):
        return self.name

class Box(models.Model):
    """
    A Box represents a box in which aliquots are stored.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rack = models.ForeignKey(Rack, on_delete=models.PROTECT, related_name='boxes')
    rows = models.IntegerField()
    columns = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "boxes"

    @property
    def auto_store_enabled(self):
        """Check if auto-store is enabled for this box (inherited from device)."""
        return self.rack.shelf.device.auto_store_enabled

    @property
    def aliquots(self):
        """Get all aliquots in this box."""
        from sample.models.aliquot import AliquotLocation
        return AliquotLocation.objects.filter(box=self)
    def get_available_slots(self):
        """Get available slots in this box for auto-storage."""
        from sample.models.aliquot import AliquotLocation
        # Get all occupied slots
        occupied_slots = AliquotLocation.objects.filter(box=self).values_list('row', 'column')
        occupied_set = set(occupied_slots)
        # Find available slots
        available_slots = []
        for row in range(1, self.rows + 1):
            for col in range(1, self.columns + 1):
                if (row, col) not in occupied_set:
                    available_slots.append({
                        'row': row,
                        'column': col
                    })
        return available_slots
    def has_available_slots(self):
        """Check if this box has any available slots."""
        return len(self.get_available_slots()) > 0