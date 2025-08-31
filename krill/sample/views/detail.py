from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation, AliquotTube
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
        
        # Add storage location information for aliquots
        if self.kwargs.get('type') == 'aliquot':
            # Get all tubes for this aliquot
            tubes = AliquotTube.objects.filter(aliquot=self.object).select_related('disposition')
            context['tubes'] = tubes
            
            # Get storage locations for stored tubes
            stored_tubes = tubes.filter(disposition__dispositionType='stored')
            if stored_tubes.exists():
                locations = AliquotLocation.objects.filter(
                    aliquot=self.object,
                    tube_number__in=stored_tubes.values_list('tube_number', flat=True)
                ).select_related('box__rack__shelf__device')
                
                if locations.exists():
                    context['storage_locations'] = []
                    for location in locations:
                        context['storage_locations'].append({
                            'box': location.box,
                            'row': location.row,
                            'column': location.column,
                            'tube_number': location.tube_number,
                            'device': location.box.rack.shelf.device,
                            'shelf': location.box.rack.shelf,
                            'rack': location.box.rack,
                        })
                else:
                    context['storage_locations'] = None
            else:
                context['storage_locations'] = None
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form_class()(request.POST, instance=self.object)
        
        if form.is_valid():
            form.save()
            return redirect('sample:list')
        
        return render(request, self.template_name, {'object': self.object, 'form': form})

@method_decorator(login_required, name='dispatch')
class TubeDetailView(DetailView):
    model = AliquotTube
    template_name = 'sample/tube_detail.html'
    context_object_name = 'tube'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tube = self.object
        
        # Get storage location if tube is stored
        if tube.disposition.dispositionType == 'stored':
            try:
                location = AliquotLocation.objects.get(
                    aliquot=tube.aliquot,
                    tube_number=tube.tube_number
                )
                context['storage_location'] = {
                    'box': location.box,
                    'row': location.row,
                    'column': location.column,
                    'device': location.box.rack.shelf.device,
                    'shelf': location.box.rack.shelf,
                    'rack': location.box.rack,
                }
            except AliquotLocation.DoesNotExist:
                context['storage_location'] = None
        else:
            context['storage_location'] = None
        
        return context