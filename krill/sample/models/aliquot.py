from django.db import models
from storage.models import Box
from django.core.validators import MinValueValidator, MaxValueValidator

class AliquotType(models.Model):
    name = models.CharField(max_length=200, unique=True, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True)
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
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Aliquot(models.Model):
    parent = models.ForeignKey(to='Aliquot', on_delete=models.PROTECT, null=True, blank=True)
    sample = models.ForeignKey(to='sample.Sample', on_delete=models.PROTECT, null=False, blank=False)
    quantity = models.IntegerField(default=0, null=False, blank=False)
    aliquotType = models.ForeignKey(to='AliquotType', on_delete=models.PROTECT, null=False, blank=False)
    disposition = models.ForeignKey(to='AliquotDisposition', on_delete=models.PROTECT, null=False, blank=False)
    passage = models.CharField(max_length=200, default=0)
    experiment = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sample.name} - {self.aliquotType.name} - {self.quantity}"

class AliquotLocation(models.Model):
    aliquot = models.ForeignKey(to='Aliquot', on_delete=models.PROTECT, null=False, blank=False)
    box = models.ForeignKey(to='storage.Box', on_delete=models.PROTECT, null=False, blank=False)
    row = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)], null=False, blank=False)
    column = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)], null=False, blank=False)
    
