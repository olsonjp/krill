from django.contrib import admin
from .models import (
    ConsumableRoom, ConsumableLocation,
    Vendor, ConsumableType, Consumable,
)


@admin.register(ConsumableRoom)
class ConsumableRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(ConsumableLocation)
class ConsumableLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'room', 'kind']
    list_filter = ['kind', 'room']
    search_fields = ['name', 'description']


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'account_number']
    search_fields = ['name', 'account_number']


@admin.register(ConsumableType)
class ConsumableTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'icon']
    list_filter = ['category']
    search_fields = ['name', 'description']


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ['name', 'consumable_type', 'vendor', 'quantity', 'unit', 'deleted']
    list_filter = ['consumable_type', 'deleted', 'access_level']
    search_fields = ['name', 'catalog_number', 'lot_number']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
