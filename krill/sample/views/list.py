from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotDisposition, AliquotLocation
from ..models.source import Source

class SampleListView(LoginRequiredMixin, ListView):
    template_name = 'sample/list.html'
    context_object_name = 'items'

    def get_queryset(self):
        model_type = self.request.GET.get('type', 'sample')

        if model_type == 'aliquot':
            queryset = Aliquot.objects.select_related(
                'sample',
                'aliquot_type',
                'disposition',
                'location__box__rack__shelf__device__site',
            )
        elif model_type == 'aliquot-type':
            queryset = AliquotType.objects.all()
        elif model_type == 'source':
            queryset = Source.objects.all()
        else:
            queryset = Sample.objects.select_related('source')

        # Text search
        search_query = self.request.GET.get('q', '')
        if search_query:
            if model_type == 'aliquot':
                queryset = queryset.filter(
                    Q(sample__name__icontains=search_query) |
                    Q(aliquot_type__name__icontains=search_query)
                )
            elif model_type in ('sample', 'source', 'aliquot-type'):
                queryset = queryset.filter(name__icontains=search_query)

        # Aliquot-specific filters
        if model_type == 'aliquot':
            disposition_filter = self.request.GET.get('disposition', '')
            if disposition_filter:
                queryset = queryset.filter(disposition__disposition_type=disposition_filter)

            aliquot_type_filter = self.request.GET.get('aliquot_type', '')
            if aliquot_type_filter:
                queryset = queryset.filter(aliquot_type__id=aliquot_type_filter)

        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        sort_order = self.request.GET.get('order', 'asc')

        if sort_order == 'desc':
            sort_prefix = '-'
        else:
            sort_prefix = ''

        if model_type == 'aliquot' and sort_by == 'disposition':
            queryset = queryset.order_by('sample__name', 'id')
        elif model_type == 'aliquot' and sort_by == 'type':
            queryset = queryset.order_by(f'{sort_prefix}aliquot_type__name', 'id')
        elif model_type == 'aliquot' and sort_by == 'sample':
            queryset = queryset.order_by(f'{sort_prefix}sample__name', 'id')
        elif model_type == 'aliquot' and sort_by == 'created_at':
            queryset = queryset.order_by(f'{sort_prefix}created_at', 'id')
        elif hasattr(queryset.model, sort_by):
            try:
                queryset.model._meta.get_field(sort_by)
                queryset = queryset.order_by(f'{sort_prefix}{sort_by}')
            except Exception:
                queryset = queryset.order_by('sample__name', 'id') if model_type == 'aliquot' else queryset.order_by('name', 'id')
        else:
            if model_type == 'aliquot':
                queryset = queryset.order_by('sample__name', 'id')
            elif hasattr(queryset.model, 'name'):
                queryset = queryset.order_by('name', 'id')
            else:
                queryset = queryset.order_by('id')

        return queryset

    def get_paginate_by(self, queryset):
        if self.request.GET.get('page_size') == '20':
            return 20
        return 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'sample')
        context['model_type'] = model_type

        if model_type == 'aliquot':
            context['model_name'] = 'Aliquots'
        elif model_type == 'aliquot-type':
            context['model_name'] = 'Aliquot Types'
        elif model_type == 'source':
            context['model_name'] = 'Sources'
        else:
            context['model_name'] = 'Samples'

        context['search_query'] = self.request.GET.get('q', '')
        context['sort_by'] = self.request.GET.get('sort', 'name')
        context['sort_order'] = self.request.GET.get('order', 'asc')

        # Aliquot filter context
        context['disposition_filter'] = self.request.GET.get('disposition', '')
        context['aliquot_type_filter'] = self.request.GET.get('aliquot_type', '')
        context['disposition_choices'] = AliquotDisposition.DISPOSITION_CHOICES
        context['aliquot_types'] = AliquotType.objects.order_by('name')

        return context
