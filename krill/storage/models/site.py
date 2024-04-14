from django.db import models

class Site(models.Model):
    """
    A Site represents a physical locale where Samples are stored.
    """
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class Location(models.Model):
    """
    A Location represents a specific building or office where Samples are stored.
    """
    name = models.CharField(max_length=200)
    site = models.ForeignKey(to='storage.Site',
        on_delete=models.PROTECT)

    def __str__(self):
        return self.name