from django.contrib import admin
from .models import Sample, Aliquot, AliquotDisposition, AliquotType

admin.site.register(Sample)
admin.site.register(Aliquot)
admin.site.register(AliquotDisposition)
admin.site.register(AliquotType)
