from django.db import models
from storage.models import Box

class AliquotType(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    def __str__(self):
        return self.name

class AliquotDisposition(models.Model):
    TYPES = (
        ('stored', 'Stored'),
        ('exhausted', 'Exhausted'),
        ('in_use', 'In Use'),
    )
    name = models.CharField(max_length=200)
    dispositionType = models.CharField(max_length = 32, choices = TYPES, default = 'stored')
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Aliquot(models.Model):
    sample = models.ForeignKey(to='sample.Sample',
        on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    box = models.ForeignKey(to='storage.Box', on_delete=models.PROTECT)
    row = models.PositiveSmallIntegerField(default=1)
    column = models.PositiveSmallIntegerField(default=1)
    aliquotType = models.ForeignKey(to='AliquotType', on_delete=models.PROTECT)
    disposition = models.ForeignKey(to='AliquotDisposition', on_delete=models.PROTECT)
    passage = models.CharField(max_length=200, default=0)
    notes = models.TextField(blank=True)