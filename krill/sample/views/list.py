from django.views.generic import ListView
from django.shortcuts import render
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotDisposition

class SampleListView(ListView):
    model = Sample
    template_name = 'sample/list.html'
    context_object_name = 'samples'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['aliquots'] = Aliquot.objects.all()
        context['aliquot_types'] = AliquotType.objects.all()
        context['aliquot_dispositions'] = AliquotDisposition.objects.all()
        return context 