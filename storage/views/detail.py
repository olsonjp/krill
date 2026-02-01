from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from ..models.storage import Box, Rack, Shelf, Device
from ..models.site import Site
from ..forms import BoxForm, RackForm, ShelfForm, DeviceForm, SiteForm
from sample.models.aliquot import AliquotLocation

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
        # Add storage information for boxes
        if self.kwargs.get('type') == 'box':
            box = self.object
            # Only show tubes that are currently stored (disposition is "Stored")
            locations = AliquotLocation.objects.filter(
                box=box
            ).select_related('aliquot__sample')
            # Create a grid representation of the box
            box_grid = []
            for row in range(1, box.rows + 1):
                row_data = []
                for col in range(1, box.columns + 1):
                    try:
                        location = locations.get(row=row, column=col)
                        row_data.append({
                            'row': row,
                            'column': col,
                            'occupied': True,
                            'aliquot': location.aliquot,
                            'sample': location.aliquot.sample,
                            'tube_number': location.tube_number
                        })
                    except AliquotLocation.DoesNotExist:
                        row_data.append({
                            'row': row,
                            'column': col,
                            'occupied': False,
                            'aliquot': None,
                            'sample': None,
                            'tube_number': None
                        })
                box_grid.append(row_data)
            context['box_grid'] = box_grid
            context['total_slots'] = box.rows * box.columns
            context['used_slots'] = locations.count()
            context['available_slots'] = context['total_slots'] - context['used_slots']
            context['storage_percentage'] = (context['used_slots'] / context['total_slots']) * 100 if context['total_slots'] > 0 else 0
            context['locations'] = locations
            # Add available aliquots for assignment
            from sample.models.aliquot import Aliquot
            context['available_aliquots'] = Aliquot.objects.all().select_related('sample', 'aliquot_type').order_by('sample__name')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form_class()(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            return redirect('storage:storage_list')
        return render(request, self.template_name, {'object': self.object, 'form': form})
