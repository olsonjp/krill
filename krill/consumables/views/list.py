from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from ..models.consumable import Consumable
from ..models.consumable_type import ConsumableType
from ..models.location import ConsumableRoom, ConsumableLocation
from ..models.vendor import Vendor
from .mixins import ConsumablesEnabledMixin


class ConsumablesListView(ConsumablesEnabledMixin, LoginRequiredMixin, ListView):
    template_name = 'consumables/list.html'
    context_object_name = 'items'

    def get_paginate_by(self, queryset):
        return 20 if self.request.GET.get('page_size') == '20' else 50

    def _model_type(self):
        return self.request.GET.get('type', 'consumable')

    def get_queryset(self):
        model_type = self._model_type()
        q = self.request.GET.get('q', '')

        if model_type == 'type':
            qs = ConsumableType.objects.all()
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        elif model_type == 'vendor':
            qs = Vendor.objects.all()
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(account_number__icontains=q))
        elif model_type == 'room':
            qs = ConsumableRoom.objects.all()
            if q:
                qs = qs.filter(name__icontains=q)
        elif model_type == 'location':
            qs = ConsumableLocation.objects.select_related('room')
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(room__name__icontains=q))
        else:  # consumable (default)
            qs = Consumable.objects.active().select_related(
                'consumable_type', 'vendor', 'location__room'
            )
            if q:
                qs = qs.filter(
                    Q(name__icontains=q)
                    | Q(catalog_number__icontains=q)
                    | Q(consumable_type__name__icontains=q)
                    | Q(vendor__name__icontains=q)
                )
            # Category filter
            category = self.request.GET.get('category', '')
            if category:
                qs = qs.filter(consumable_type__category=category)

        # Sorting
        sort_map = {
            'consumable': {'type': 'consumable_type__name', 'vendor': 'vendor__name', 'location': 'location__name'},
            'location': {'room': 'room__name'},
        }
        raw_sort = self.request.GET.get('sort', 'name')
        mapped = sort_map.get(model_type, {}).get(raw_sort, raw_sort)
        order = self.request.GET.get('order', 'asc')
        try:
            qs.model._meta.get_field(mapped.lstrip('-').split('__')[0])
            sort_field = f'-{mapped}' if order == 'desc' else mapped
        except Exception:
            sort_field = 'name'
        return qs.order_by(sort_field, 'id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self._model_type()
        names = {
            'consumable': 'Consumables',
            'type': 'Consumable Types',
            'vendor': 'Vendors',
            'room': 'Rooms',
            'location': 'Locations',
        }
        context['model_type'] = model_type
        context['model_name'] = names.get(model_type, 'Consumables')
        context['search_query'] = self.request.GET.get('q', '')
        context['sort_by'] = self.request.GET.get('sort', 'name')
        context['sort_order'] = self.request.GET.get('order', 'asc')
        context['selected_category'] = self.request.GET.get('category', '')
        from ..models.consumable_type import ConsumableType
        context['consumable_categories'] = ConsumableType.CATEGORY_CHOICES
        # Build query string without page for pagination links
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_string'] = params.urlencode()
        return context
