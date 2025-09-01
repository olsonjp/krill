from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.storage import Box, Rack, Shelf, Device
from ..models.site import Site
from ..forms import BoxForm, ShelfForm, DeviceForm, SiteForm

@method_decorator(login_required, name='dispatch')
class StorageCreateView(CreateView):
    template_name = 'storage/create.html'
    def get_form_class(self):
        model_type = self.request.GET.get('type', 'site')
        if model_type == 'box':
            return BoxForm
        elif model_type == 'shelf':
            return ShelfForm
        elif model_type == 'device':
            return DeviceForm
        else:
            return SiteForm
    def get_success_url(self):
        model_type = self.request.GET.get('type', 'site')
        return f"{reverse_lazy('storage:list')}?type={model_type}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'site')
        context['model_type'] = model_type
        context['model_name'] = model_type.title()
        return context 