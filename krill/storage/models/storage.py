from django.db import models

class Device(models.Model):
    """
    A Device represents a freezer or dewer in which Samples are stored.
    """
    name = models.CharField(max_length=200)
    site = models.ForeignKey(to='storage.Site',
        on_delete=models.PROTECT)
    shelves = models.IntegerField()
    
    def __str__(self):
        return self.name

class Shelf(models.Model):
    """
    A Shelf represents a shelf in a freezer in which Samples are stored. Dewers will have a single shelf.
    """
    name = models.CharField(max_length=200)
    site = models.ForeignKey(to='storage.Device',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "shelves"

    def __str__(self):
        return self.name

class Rack(models.Model):
    """
    A Rack represents a rack in a freezer or dewer in which Samples are stored.
    """
    name = models.CharField(max_length=200)
    site = models.ForeignKey(to='storage.Shelf',
        on_delete=models.PROTECT)

    def __str__(self):
        return self.name

class Box(models.Model):
    """
    A Box represents a box in which aliquots are stored.
    """
    name = models.CharField(max_length=200)
    rows = models.PositiveSmallIntegerField(default=1)
    columns = models.PositiveSmallIntegerField(default=1)
    site = models.ForeignKey(to='storage.Rack',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "boxes"

    def __str__(self):
        return self.name