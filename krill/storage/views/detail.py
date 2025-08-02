from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.storage import Box, Rack, Shelf, Device
from ..models.site import Site
from ..forms import BoxForm, RackForm, ShelfForm, DeviceForm, SiteForm

@method_decorator(login_required, name='dispatch')
class StorageDetailView(DetailView):
    template_name = 'storage/detail.html'
    
    def get_object(self):
        model_type = self.kwargs.get('type', 'site')
        pk = self.kwargs.get('pk')
        
        if model_type == 'box':
            return get_object_or_404(Box, pk=pk)
        elif model_type == 'shelf':
            return get_object_or_404(Shelf, pk=pk)
        elif model_type == 'device':
            return get_object_or_404(Device, pk=pk)
        else:
            return get_object_or_404(Site, pk=pk)
    
    def get_form_class(self):
        model_type = self.kwargs.get('type', 'site')
        
        if model_type == 'box':
            return BoxForm
        elif model_type == 'shelf':
            return ShelfForm
        elif model_type == 'device':
            return DeviceForm
        else:
            return SiteForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_type'] = self.kwargs.get('type', 'site')
        context['form'] = self.get_form_class()(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form_class()(request.POST, instance=self.object)
        
        if form.is_valid():
            form.save()
            return redirect('storage:list')
        
        return render(request, self.template_name, {'object': self.object, 'form': form})