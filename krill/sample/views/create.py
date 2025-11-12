from django.views.generic.edit import CreateView
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotDisposition, AliquotLocation
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
        return f"{reverse('sample:sample_list')}?type={model_type}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.request.GET.get('type', 'sample')
        context['model_type'] = model_type
        context['model_name'] = model_type.replace('-', ' ').title()
        return context

    def form_valid(self, form):
        """Handle form submission and box assignment if requested"""
        response = super().form_valid(form)

        # If this is an aliquot form, create tubes
        if isinstance(form, AliquotForm):
            # Create tubes for the aliquot (if not already created)
            if not hasattr(self.object, '_tubes_created'):
                self.object.create_tubes(auto_store=False)

        # If box assignment is requested
        if isinstance(form, AliquotForm) and form.cleaned_data.get('assign_to_box') and form.cleaned_data.get('box'):
            box = form.cleaned_data['box']
            start_row = form.cleaned_data.get('start_row')
            start_column = form.cleaned_data.get('start_column')

            # Get stored disposition
            stored_disposition, _ = AliquotDisposition.objects.get_or_create(
                name='Stored',
                defaults={'disposition_type': 'stored'}
            )

            # Get available slots
            available_slots = box.get_available_slots()
            if not available_slots:
                # No available slots - could add a message here
                return response

            # Determine starting position
            if start_row and start_column:
                # Use specified starting position
                current_row = start_row
                current_column = start_column
            else:
                # Use first available slot
                first_slot = available_slots[0]
                current_row = first_slot['row']
                current_column = first_slot['column']

            # Assign tubes to box positions
            tubes = self.object.tubes.all().order_by('tube_number')
            for tube in tubes:
                # Find next available slot starting from current position
                slot_found = False
                for row in range(current_row, box.rows + 1):
                    start_col = current_column if row == current_row else 1
                    for col in range(start_col, box.columns + 1):
                        # Check if slot is available
                        if not AliquotLocation.objects.filter(box=box, row=row, column=col).exists():
                            # Create location
                            AliquotLocation.objects.create(
                                aliquot=self.object,
                                box=box,
                                row=row,
                                column=col,
                                tube_number=tube.tube_number
                            )
                            # Update tube disposition to stored
                            tube.disposition = stored_disposition
                            tube.save()
                            current_row = row
                            current_column = col + 1
                            slot_found = True
                            break
                    if slot_found:
                        break
                    current_column = 1
                if not slot_found:
                    # No more available slots
                    break

        return response
