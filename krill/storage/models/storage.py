from django.db import models
from .site import Site

class Device(models.Model):
    """
    A Device represents a freezer or dewer in which Samples are stored.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='devices')
    
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
    def aliquots(self):
        """Get all aliquots in this box."""
        from sample.models.aliquot import AliquotLocation
        return AliquotLocation.objects.filter(box=self)