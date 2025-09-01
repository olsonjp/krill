from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
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
                'aliquot_type'
            ).prefetch_related(
                'locations__box',
                'tubes__disposition',
                'tubes'
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
                    name__icontains=search_query
                ) | queryset.filter(
                    sample__name__icontains=search_query
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
        
        # Apply sorting to queryset
        if hasattr(queryset.model, sort_by.replace('-', '')):
            queryset = queryset.order_by(sort_by)
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