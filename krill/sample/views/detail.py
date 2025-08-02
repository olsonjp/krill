from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm

@method_decorator(login_required, name='dispatch')
class ModelDetailView(DetailView):
    template_name = 'sample/detail.html'
    
    def get_object(self):
        model_type = self.kwargs.get('type', 'sample')
        pk = self.kwargs.get('pk')
        
        if model_type == 'aliquot':
            return get_object_or_404(Aliquot, pk=pk)
        elif model_type == 'aliquot-type':
            return get_object_or_404(AliquotType, pk=pk)
        elif model_type == 'source':
            return get_object_or_404(Source, pk=pk)
        else:
            return get_object_or_404(Sample, pk=pk)
    
    def get_form_class(self):
        model_type = self.kwargs.get('type', 'sample')
        
        if model_type == 'aliquot':
            return AliquotForm
        elif model_type == 'aliquot-type':
            return AliquotTypeForm
        elif model_type == 'source':
            return SourceForm
        else:
            return SampleForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_type'] = self.kwargs.get('type', 'sample')
        context['form'] = self.get_form_class()(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form_class()(request.POST, instance=self.object)
        
        if form.is_valid():
            form.save()
            return redirect('sample:list')
        
        return render(request, self.template_name, {'object': self.object, 'form': form})