from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import CharField, F, Q
from django.db.models.functions import Cast
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
                queryset = self._search_aliquots(queryset, search_query)
            elif model_type in ('sample', 'source', 'aliquot-type'):
                queryset = queryset.filter(name__icontains=search_query)

        # Aliquot-specific filters
        if model_type == 'aliquot':
            disposition_filter = self.request.GET.get('disposition', '')
            valid_dispositions = [c[0] for c in AliquotDisposition.DISPOSITION_CHOICES]
            if disposition_filter and disposition_filter in valid_dispositions:
                queryset = queryset.filter(disposition__disposition_type=disposition_filter)

            aliquot_type_filter = self.request.GET.get('aliquot_type', '')
            if aliquot_type_filter:
                try:
                    queryset = queryset.filter(aliquot_type__id=int(aliquot_type_filter))
                except (ValueError, TypeError):
                    pass

            sample_filter = self.request.GET.get('sample', '')
            if sample_filter.isdigit():
                queryset = queryset.filter(sample_id=int(sample_filter))

            # ?checked_out_by=me: aliquots the signed-in user has checked out and not yet exhausted
            if self.request.GET.get('checked_out_by') == 'me':
                queryset = queryset.filter(
                    checked_out_by=self.request.user,
                    disposition__disposition_type='in_use',
                )

            # Hide finished (exhausted) aliquots. Disposed ones stay visible.
            if self.request.GET.get('hide_finished') == '1':
                queryset = queryset.exclude(disposition__disposition_type='exhausted')

        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        sort_order = self.request.GET.get('order', 'asc')

        if sort_order == 'desc':
            sort_prefix = '-'
        else:
            sort_prefix = ''

        if model_type == 'aliquot' and sort_by == 'disposition':
            queryset = queryset.order_by(f'{sort_prefix}disposition__disposition_type', 'id')
        elif model_type == 'aliquot' and sort_by == 'type':
            queryset = queryset.order_by(f'{sort_prefix}aliquot_type__name', 'id')
        elif model_type == 'aliquot' and sort_by == 'sample':
            queryset = queryset.order_by(f'{sort_prefix}sample__name', 'id')
        elif model_type == 'aliquot' and sort_by == 'sample_date':
            # Blank dates sort last in both directions
            date_order = F('sample_date').desc(nulls_last=True) if sort_order == 'desc' else F('sample_date').asc(nulls_last=True)
            queryset = queryset.order_by(date_order, 'id')
        elif model_type == 'aliquot' and sort_by == 'passage':
            queryset = queryset.order_by(f'{sort_prefix}passage', 'id')
        elif model_type == 'aliquot' and sort_by == 'location':
            queryset = queryset.order_by(f'{sort_prefix}location__box__rack__shelf__device__name', 'id')
        elif model_type == 'sample' and sort_by == 'source':
            queryset = queryset.order_by(f'{sort_prefix}source__name', 'id')
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

    @staticmethod
    def _search_aliquots(queryset, term):
        """Match the term against any aliquot field shown or recorded in Krill."""
        term = term.strip()
        queryset = queryset.annotate(sample_date_text=Cast('sample_date', CharField()))
        match = (
            Q(sample__name__icontains=term) |
            Q(sample__experiment__icontains=term) |
            Q(sample__notes__icontains=term) |
            Q(aliquot_type__name__icontains=term) |
            Q(disposition__name__icontains=term) |
            Q(passage__icontains=term) |
            Q(lab_member_initials__icontains=term) |
            Q(lab_member__first_name__icontains=term) |
            Q(lab_member__last_name__icontains=term) |
            Q(lab_member__username__icontains=term) |
            Q(sample_date_text__icontains=term) |
            Q(location__box__name__icontains=term) |
            Q(location__box__rack__shelf__device__name__icontains=term)
        )
        # Aliquot number: "12" or "#12" matches aliquot 12 exactly
        number = term.lstrip('#')
        if number.isdigit():
            match |= Q(id=int(number))
        return queryset.filter(match)

    def _toggle_url(self, param, value):
        """Link that flips one yes/no filter, keeps every other parameter, and goes back to page 1."""
        params = self.request.GET.copy()
        params.pop('page', None)
        if params.get(param) == value:
            params.pop(param)
        else:
            params[param] = value
        query = params.urlencode()
        return f'?{query}' if query else self.request.path

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

        # Build a query string with all current params except 'page' for pagination links
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_string'] = params.urlencode()

        # Aliquot filter context
        if model_type == 'aliquot':
            context['disposition_filter'] = self.request.GET.get('disposition', '')
            context['aliquot_type_filter'] = self.request.GET.get('aliquot_type', '')
            context['hide_finished'] = self.request.GET.get('hide_finished') == '1'
            context['checked_out_by_me'] = self.request.GET.get('checked_out_by') == 'me'
            context['checked_out_toggle_url'] = self._toggle_url('checked_out_by', 'me')
            context['hide_finished_toggle_url'] = self._toggle_url('hide_finished', '1')
            context['checked_out_count'] = Aliquot.objects.filter(
                checked_out_by=self.request.user,
                disposition__disposition_type='in_use',
            ).count()
            sample_filter = self.request.GET.get('sample', '')
            context['sample_filter'] = Sample.objects.filter(pk=int(sample_filter)).first() if sample_filter.isdigit() else None
            context['disposition_choices'] = AliquotDisposition.DISPOSITION_CHOICES
            context['aliquot_types'] = AliquotType.objects.order_by('name')
        else:
            context['disposition_filter'] = ''
            context['aliquot_type_filter'] = ''
            context['hide_finished'] = False
            context['checked_out_by_me'] = False
            context['sample_filter'] = None
            context['disposition_choices'] = []
            context['aliquot_types'] = AliquotType.objects.none()

        return context
