from django.views.generic import ListView
from django.shortcuts import render
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source

class SampleListView(ListView):
    template_name = 'sample/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'sample')
        
        if model_type == 'aliquot':
            context['items'] = Aliquot.objects.select_related(
                'sample', 
                'aliquotType', 
                'disposition'
            ).prefetch_related(
                'aliquotlocation_set__box'
            ).all()
            context['model_name'] = 'Aliquots'
        elif model_type == 'aliquot-type':
            context['items'] = AliquotType.objects.all()
            context['model_name'] = 'Aliquot Types'
        elif model_type == 'source':
            context['items'] = Source.objects.all()
            context['model_name'] = 'Sources'
        else:  # default to samples
            context['items'] = Sample.objects.all()
            context['model_name'] = 'Samples'
            
        return context

    def get_queryset(self):
        return []  # We're using context['items'] instead 