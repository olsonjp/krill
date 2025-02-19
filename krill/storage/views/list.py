from django.views.generic import ListView
from django.shortcuts import render
from ..models.storage import Device, Shelf, Rack, Box
from ..models.site import Site

class StorageListView(ListView):
    template_name = 'storage/list.html'
    context_object_name = 'sites'
    model = Site

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.all()
        context['shelves'] = Shelf.objects.all()
        context['racks'] = Rack.objects.all()
        context['boxes'] = Box.objects.all()
        return context 