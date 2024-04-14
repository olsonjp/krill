from django.contrib import admin
from .models import Site, Location, Device, Shelf, Rack, Box

admin.site.register(Site)
admin.site.register(Location)
admin.site.register(Device)
admin.site.register(Shelf)
admin.site.register(Rack)
admin.site.register(Box)