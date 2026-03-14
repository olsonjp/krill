from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source

class SampleListView(LoginRequiredMixin, ListView):
    template_name = 'sample/list.html'
    paginate_by = 20
    context_object_name = 'items'

    def get_queryset(self):
        model_type = self.request.GET.get('type', 'sample')

        # Get the queryset based on model type
        if model_type == 'aliquot':
            queryset = Aliquot.objects.select_related(
                'sample',
                'aliquot_type',
                'disposition',
                'location__box',
            )
        elif model_type == 'aliquot-type':
            queryset = AliquotType.objects.all()
        elif model_type == 'source':
            queryset = Source.objects.all()
        else:  # default to samples
            queryset = Sample.objects.select_related('source')

        # Apply search filtering if provided
        search_query = self.request.GET.get('q', '')
        if search_query:
            if model_type == 'aliquot':
                queryset = queryset.filter(
                    Q(sample__name__icontains=search_query) |
                    Q(aliquot_type__name__icontains=search_query)
                )
            elif model_type == 'sample':
                queryset = queryset.filter(name__icontains=search_query)
            elif model_type == 'source':
                queryset = queryset.filter(name__icontains=search_query)
            elif model_type == 'aliquot-type':
                queryset = queryset.filter(name__icontains=search_query)

        # Apply sorting
        sort_by = self.request.GET.get('sort', 'name')
        sort_order = self.request.GET.get('order', 'asc')

        if sort_order == 'desc':
            sort_by = f'-{sort_by}'

        # Handle special cases for computed properties and non-database fields
        if model_type == 'aliquot' and sort_by.replace('-', '') == 'disposition':
            # Disposition is a computed property, so we can't sort by it directly
            # Instead, sort by sample name and id for consistent pagination
            queryset = queryset.order_by('sample__name', 'id')
        elif model_type == 'aliquot' and sort_by.replace('-', '') == 'type':
            # Map 'type' to 'aliquot_type__name' for proper sorting
            sort_field = 'aliquot_type__name' if not sort_by.startswith('-') else '-aliquot_type__name'
            queryset = queryset.order_by(sort_field, 'id')
        elif model_type == 'aliquot' and sort_by.replace('-', '') == 'sample':
            # Map 'sample' to 'sample__name' for proper sorting
            sort_field = 'sample__name' if not sort_by.startswith('-') else '-sample__name'
            queryset = queryset.order_by(sort_field, 'id')
        elif hasattr(queryset.model, sort_by.replace('-', '')):
            # Check if it's actually a database field, not just a property
            field_name = sort_by.replace('-', '')
            field = queryset.model._meta.get_field(field_name)
            if field:
                queryset = queryset.order_by(sort_by)
            else:
                # It's a property, not a field, so use default sorting
                if model_type == 'aliquot':
                    queryset = queryset.order_by('sample__name', 'id')
                elif hasattr(queryset.model, 'name'):
                    queryset = queryset.order_by('name', 'id')
                else:
                    queryset = queryset.order_by('id')
        else:
            # Default sorting - use appropriate field for consistent pagination
            if model_type == 'aliquot':
                queryset = queryset.order_by('sample__name', 'id')
            elif hasattr(queryset.model, 'name'):
                queryset = queryset.order_by('name', 'id')
            else:
                queryset = queryset.order_by('id')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'sample')

        # Set model name
        if model_type == 'aliquot':
            context['model_name'] = 'Aliquots'
        elif model_type == 'aliquot-type':
            context['model_name'] = 'Aliquot Types'
        elif model_type == 'source':
            context['model_name'] = 'Sources'
        else:  # default to samples
            context['model_name'] = 'Samples'

        # Add search and sort context
        context['search_query'] = self.request.GET.get('q', '')
        context['sort_by'] = self.request.GET.get('sort', 'name')
        context['sort_order'] = self.request.GET.get('order', 'asc')

        return context
