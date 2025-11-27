from django.views.generic.edit import CreateView
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db import IntegrityError, transaction
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
            requested_position_used = False
            if start_row and start_column:
                # Validate bounds (form validation should catch this, but double-check)
                if start_row > box.rows or start_column > box.columns:
                    # Invalid bounds - fall back to auto-assignment
                    first_slot = available_slots[0]
                    current_row = first_slot['row']
                    current_column = first_slot['column']
                    messages.warning(
                        self.request,
                        f"Requested position ({start_row}, {start_column}) exceeds box dimensions. "
                        f"Using first available position ({current_row}, {current_column}) instead."
                    )
                else:
                    # Check if requested position is available
                    if AliquotLocation.objects.filter(box=box, row=start_row, column=start_column).exists():
                        # Position is occupied - find next available slot starting from requested position
                        # This will be handled by the assignment loop below, but we'll warn the user
                        current_row = start_row
                        current_column = start_column
                        # Find the actual first available slot starting from requested position
                        actual_start_row = None
                        actual_start_col = None
                        for row in range(start_row, box.rows + 1):
                            start_col = start_column if row == start_row else 1
                            for col in range(start_col, box.columns + 1):
                                if not AliquotLocation.objects.filter(box=box, row=row, column=col).exists():
                                    actual_start_row = row
                                    actual_start_col = col
                                    break
                            if actual_start_row is not None:
                                break

                        if actual_start_row is not None:
                            current_row = actual_start_row
                            current_column = actual_start_col
                            messages.warning(
                                self.request,
                                f"Requested position ({start_row}, {start_column}) is already occupied. "
                                f"Starting from next available position ({current_row}, {current_column})."
                            )
                        else:
                            # No available slots starting from requested position - use first available
                            first_slot = available_slots[0]
                            current_row = first_slot['row']
                            current_column = first_slot['column']
                            messages.warning(
                                self.request,
                                f"Requested position ({start_row}, {start_column}) is occupied and no slots available from that position. "
                                f"Using first available position ({current_row}, {current_column}) instead."
                            )
                    else:
                        # Use specified starting position
                        current_row = start_row
                        current_column = start_column
                        requested_position_used = True
            else:
                # Use first available slot
                first_slot = available_slots[0]
                current_row = first_slot['row']
                current_column = first_slot['column']

            # Assign tubes to box positions with race condition handling
            tubes = self.object.tubes.all().order_by('tube_number')
            tubes_assigned = 0
            max_retries = 3  # Maximum retries per tube to find available slot

            for tube in tubes:
                # Find next available slot starting from current position
                slot_found = False
                retry_count = 0

                while not slot_found and retry_count < max_retries:
                    for row in range(current_row, box.rows + 1):
                        start_col = current_column if row == current_row else 1
                        for col in range(start_col, box.columns + 1):
                            # Try to create location with race condition handling
                            try:
                                with transaction.atomic():
                                    # Double-check slot is available within transaction
                                    if AliquotLocation.objects.filter(box=box, row=row, column=col).exists():
                                        continue  # Skip to next slot

                                    # Create location atomically
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
                                    tubes_assigned += 1
                                    break
                            except IntegrityError:
                                # Race condition: another request took this slot
                                # Continue to next slot without incrementing retry_count
                                # since we're already trying the next slot
                                continue
                        if slot_found:
                            break
                        current_column = 1

                    if not slot_found:
                        retry_count += 1
                        # Reset to start of box for retry
                        current_row = 1
                        current_column = 1

                if not slot_found:
                    # No more available slots after retries
                    messages.warning(
                        self.request,
                        f"Could not assign all tubes. {tubes_assigned} of {tubes.count()} tubes were assigned."
                    )
                    break

        return response
