from django.views.generic import ListView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.storage import Device, Shelf, Rack, Box
from ..models.site import Site

@method_decorator(login_required, name='dispatch')
class StorageListView(ListView):
    template_name = 'storage/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'site')
        
        if model_type == 'box':
            context['items'] = Box.objects.select_related(
                'rack__shelf__device__site'
            ).all()
            context['model_name'] = 'Boxes'
        elif model_type == 'shelf':
            context['items'] = Shelf.objects.select_related(
                'device__site'
            ).all()
            context['model_name'] = 'Shelves'
        elif model_type == 'device':
            context['items'] = Device.objects.select_related('site').all()
            context['model_name'] = 'Devices'
        else:  # default to sites
            context['items'] = Site.objects.all()
            context['model_name'] = 'Sites'
            
        return context

    def get_queryset(self):
        return []  # We're using context['items'] instead 