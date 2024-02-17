from django.contrib import admin
from .models import Site, Device, Shelf, Rack, Box

admin.site.register(Site)
admin.site.register(Device)
admin.site.register(Shelf)
admin.site.register(Rack)
admin.site.register(Box)