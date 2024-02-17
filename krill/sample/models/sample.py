from django.db import models
from storage.models import Box

class Sample(models.Model):
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name