from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm

@method_decorator(login_required, name='dispatch')
class ModelCreateView(CreateView):
    template_name = 'sample/create.html'
    def get_form_class(self):
        model_type = self.request.GET.get('type', 'sample')
        if model_type == 'aliquot':
            return AliquotForm
        elif model_type == 'aliquot-type':
            return AliquotTypeForm
        elif model_type == 'source':
            return SourceForm
        else:
            return SampleForm
    def get_success_url(self):
        model_type = self.request.GET.get('type', 'sample')
        return f"{reverse_lazy('sample:list')}?type={model_type}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'sample')
        context['model_type'] = model_type
        context['model_name'] = model_type.replace('-', ' ').title()
        return context 