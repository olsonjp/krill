from django.db import models

class Site(models.Model):
    """
    A Site represents a physical locale where Samples are stored.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name