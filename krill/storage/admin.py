from django.contrib import admin
from .models import Site, Device, Shelf, Rack, Box

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'site', 'auto_store_enabled']
    list_filter = ['auto_store_enabled', 'site']
    search_fields = ['name', 'description']

@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ['name', 'device']
    list_filter = ['device']
    search_fields = ['name', 'description']

@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ['name', 'shelf']
    list_filter = ['shelf__device']
    search_fields = ['name', 'description']

@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ['name', 'rack', 'rows', 'columns', 'auto_store_enabled']
    list_filter = ['rack__shelf__device__auto_store_enabled']
    search_fields = ['name', 'description']
    readonly_fields = ['auto_store_enabled']
    def auto_store_enabled(self, obj):
        return obj.auto_store_enabled
    auto_store_enabled.boolean = True
    auto_store_enabled.short_description = 'Auto-Store Enabled'