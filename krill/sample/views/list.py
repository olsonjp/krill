from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Cast, Coalesce
from .. import low_count
from ..list_filters import ALIQUOT_FILTERS, SAMPLE_FILTERS, DATE_KINDS, split_words
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotDisposition, AliquotLocation
from ..models.source import Source
from person.models import SiteConfiguration, UserRole

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
                'checked_out_by',
            )
        elif model_type == 'aliquot-type':
            queryset = AliquotType.objects.all()
        elif model_type == 'source':
            queryset = Source.objects.all()
        else:
            queryset = Sample.objects.select_related('source').with_stored_count()

        # Text search: every word must match ("quoted words" stay together)
        search_query = self.request.GET.get('q', '')
        if search_query:
            if model_type == 'aliquot':
                queryset = self._search_aliquots(queryset, search_query)
            elif model_type in ('sample', 'source', 'aliquot-type'):
                for word in split_words(search_query):
                    queryset = queryset.filter(name__icontains=word)

        # Samples: field filters (source, experiment, notes)
        if model_type == 'sample':
            queryset = SAMPLE_FILTERS.apply(queryset, self.request.GET)

        # Samples running low on stored aliquots (and not opted out of the check)
        if model_type == 'sample' and self.request.GET.get('low_count') == '1':
            warn_default = SiteConfiguration.load().low_count_warn
            queryset = (
                queryset.filter(aliquot_total__gt=0, low_count_check=True)
                .annotate(warn_level=Coalesce('low_count_warn', Value(warn_default)))
                .filter(stored_count__lte=F('warn_level'))
            )

        # Aliquot-specific filters
        self.no_date_excluded = None
        if model_type == 'aliquot':
            # Field filters (sample, passage, member, location, number, disposition, type) ...
            queryset = ALIQUOT_FILTERS.apply(queryset, self.request.GET, skip_kinds=DATE_KINDS)

            sample_filter = self.request.GET.get('sample', '')
            if sample_filter.isdigit():
                queryset = queryset.filter(sample_id=int(sample_filter))

            # ?checked_out_by=me: aliquots the signed-in user has checked out and not yet exhausted
            if self.request.GET.get('checked_out_by') == 'me':
                queryset = queryset.filter(
                    checked_out_by=self.request.user,
                    disposition__disposition_type='in_use',
                )
            elif self._checked_out_by_everyone():
                # ?checked_out_by=all: everyone's, for lab managers and admins
                queryset = queryset.filter(
                    checked_out_by__isnull=False,
                    disposition__disposition_type='in_use',
                )

            # Hide finished (exhausted) aliquots. Disposed ones stay visible.
            if self.request.GET.get('hide_finished') == '1':
                queryset = queryset.exclude(disposition__disposition_type='exhausted')

            # ... and last, the date range, so we can say how many aliquots with no date it leaves out
            if any(f.kind in DATE_KINDS for f, _ in ALIQUOT_FILTERS.active(self.request.GET)):
                self.no_date_excluded = queryset.filter(sample_date__isnull=True).count()
                queryset = ALIQUOT_FILTERS.apply(queryset, self.request.GET, only_kinds=DATE_KINDS)

        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        sort_order = self.request.GET.get('order', 'asc')

        if sort_order == 'desc':
            sort_prefix = '-'
        else:
            sort_prefix = ''

        if model_type == 'aliquot' and self._checked_out_by_everyone() and 'sort' not in self.request.GET:
            # Group by person unless a column sort was chosen
            queryset = queryset.order_by('checked_out_by__username', '-checked_out_at', 'id')
        elif model_type == 'aliquot' and sort_by == 'disposition':
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
        elif model_type == 'sample' and sort_by == 'stored':
            queryset = queryset.order_by(f'{sort_prefix}stored_count', 'name', 'id')
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
        """Search every aliquot field shown or recorded in Krill.

        Every word must match something, so "hela p8" finds the p8 aliquots of HeLa. Put words in
        "quotes" to match them as one phrase.
        """
        queryset = queryset.annotate(sample_date_text=Cast('sample_date', CharField()))
        for word in split_words(term):
            match = (
                Q(sample__name__icontains=word) |
                Q(sample__experiment__icontains=word) |
                Q(sample__notes__icontains=word) |
                Q(aliquot_type__name__icontains=word) |
                Q(disposition__name__icontains=word) |
                Q(passage__icontains=word) |
                Q(lab_member_initials__icontains=word) |
                Q(lab_member__first_name__icontains=word) |
                Q(lab_member__last_name__icontains=word) |
                Q(lab_member__username__icontains=word) |
                Q(sample_date_text__icontains=word) |
                Q(location__box__name__icontains=word) |
                Q(location__box__rack__shelf__device__name__icontains=word)
            )
            # Aliquot number: "12" or "#12" matches aliquot 12 exactly
            number = word.lstrip('#')
            if number.isdigit():
                match |= Q(id=int(number))
            queryset = queryset.filter(match)
        return queryset

    def _checked_out_by_everyone(self):
        """True for ?checked_out_by=all, which only lab managers and admins may use."""
        if self.request.GET.get('checked_out_by') != 'all':
            return False
        return UserRole.get_or_create_for_user(self.request.user).role in ('lab_manager', 'lab_admin')

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

        if model_type == 'sample':
            config = SiteConfiguration.load()
            items = list(context['items'])
            for sample in items:
                sample.low_state = low_count.state_for(sample, config)
            context['items'] = items
            context['low_count_on'] = self.request.GET.get('low_count') == '1'
            context['low_count_toggle_url'] = self._toggle_url('low_count', '1')
            context['low_count_pill_count'] = sum(1 for row in low_count.low_samples() if not row['silenced'])

        context['search_query'] = self.request.GET.get('q', '')
        context['no_date_excluded'] = getattr(self, 'no_date_excluded', None)
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
            context['checked_out_all'] = self._checked_out_by_everyone()
            context['checked_out_toggle_url'] = self._toggle_url('checked_out_by', 'me')
            context['hide_finished_toggle_url'] = self._toggle_url('hide_finished', '1')
            context['checked_out_count'] = Aliquot.objects.filter(
                checked_out_by=self.request.user,
                disposition__disposition_type='in_use',
            ).count()
            sample_filter = self.request.GET.get('sample', '')
            context['sample_filter'] = Sample.objects.filter(pk=int(sample_filter)).first() if sample_filter.isdigit() else None
            extra_chips = []
            if context['checked_out_all']:
                extra_chips.append(('Checked out by anyone', 'checked_out_by'))
            if context['search_query']:
                extra_chips.append((f'"{context["search_query"]}"', 'q'))
            if context['sample_filter']:
                extra_chips.append((f'Sample: {context["sample_filter"].name}', 'sample'))
            context['filter_bar'] = ALIQUOT_FILTERS.bind(self.request, extra_chips)
            context['disposition_choices'] = AliquotDisposition.DISPOSITION_CHOICES
            context['aliquot_types'] = AliquotType.objects.order_by('name')
        else:
            context['disposition_filter'] = ''
            context['aliquot_type_filter'] = ''
            context['hide_finished'] = False
            context['checked_out_by_me'] = False
            context['checked_out_all'] = False
            context['sample_filter'] = None
            if model_type == 'sample':
                extra_chips = [(f'"{context["search_query"]}"', 'q')] if context['search_query'] else []
                context['filter_bar'] = SAMPLE_FILTERS.bind(self.request, extra_chips)
            context['disposition_choices'] = []
            context['aliquot_types'] = AliquotType.objects.none()

        return context
