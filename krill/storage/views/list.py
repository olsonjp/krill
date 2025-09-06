from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models.storage import Device, Shelf, Rack, Box
from ..models.site import Site

class StorageListView(LoginRequiredMixin, ListView):
    template_name = 'storage/list.html'
    paginate_by = 20
    context_object_name = 'items'

    def get_queryset(self):
        model_type = self.request.GET.get('type', 'site')

        # Get the queryset based on model type
        if model_type == 'box':
            queryset = Box.objects.select_related(
                'rack__shelf__device__site'
            )
        elif model_type == 'shelf':
            queryset = Shelf.objects.select_related(
                'device__site'
            )
        elif model_type == 'device':
            queryset = Device.objects.select_related('site')
        else:  # default to sites
            queryset = Site.objects.all()

        # Apply search filtering if provided
        search_query = self.request.GET.get('q', '')
        if search_query:
            if model_type == 'box':
                queryset = queryset.filter(
                    name__icontains=search_query
                ) | queryset.filter(
                    rack__shelf__device__name__icontains=search_query
                )
            elif model_type == 'shelf':
                queryset = queryset.filter(
                    name__icontains=search_query
                ) | queryset.filter(
                    device__name__icontains=search_query
                )
            elif model_type == 'device':
                queryset = queryset.filter(
                    name__icontains=search_query
                ) | queryset.filter(
                    site__name__icontains=search_query
                )
            elif model_type == 'site':
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
            # Default sorting - use id as fallback for consistent pagination
            if hasattr(queryset.model, 'name'):
                queryset = queryset.order_by('name', 'id')
            else:
                queryset = queryset.order_by('id')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'site')

        # Set model name
        if model_type == 'box':
            context['model_name'] = 'Boxes'
        elif model_type == 'shelf':
            context['model_name'] = 'Shelves'
        elif model_type == 'device':
            context['model_name'] = 'Devices'
        else:  # default to sites
            context['model_name'] = 'Sites'

        # Add search and sort context
        context['search_query'] = self.request.GET.get('q', '')
        context['sort_by'] = self.request.GET.get('sort', 'name')
        context['sort_order'] = self.request.GET.get('order', 'asc')

        return context
