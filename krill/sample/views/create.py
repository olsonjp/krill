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
from person.models import UserAuditLog

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
        model_type = self.request.GET.get('type', 'sample')

        if model_type == 'aliquot':
            return self._handle_aliquot_creation(form)

        response = super().form_valid(form)

        # Log for Recent Activity (so dashboard links work)
        if isinstance(form, SampleForm):
            UserAuditLog.log_action(
                user=self.request.user,
                action='sample_created',
                target_type='Sample',
                target_id=self.object.id,
                target_name=self.object.name,
                request=self.request,
            )

        return response

    def _handle_aliquot_creation(self, form):
        """Create one or more aliquots based on count field"""
        count = form.cleaned_data.get('count') or 1

        # Save first aliquot via standard form save
        response = super().form_valid(form)
        first_aliquot = self.object

        UserAuditLog.log_action(
            user=self.request.user,
            action='aliquot_created',
            target_type='Aliquot',
            target_id=first_aliquot.id,
            target_name=str(first_aliquot),
            request=self.request,
        )

        # Create additional aliquots if count > 1
        created_aliquots = [first_aliquot]
        for _ in range(count - 1):
            new_aliquot = Aliquot.objects.create(
                sample=first_aliquot.sample,
                aliquot_type=first_aliquot.aliquot_type,
                disposition=first_aliquot.disposition,
                parent=first_aliquot.parent,
                access_level=first_aliquot.access_level,
            )
            created_aliquots.append(new_aliquot)

        # If box assignment is requested
        if form.cleaned_data.get('assign_to_box') and form.cleaned_data.get('box'):
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
                return response

            # Determine starting position
            if start_row and start_column:
                if start_row > box.rows or start_column > box.columns:
                    first_slot = available_slots[0]
                    current_row = first_slot['row']
                    current_column = first_slot['column']
                    messages.warning(
                        self.request,
                        f"Requested position ({start_row}, {start_column}) exceeds box dimensions. "
                        f"Using first available position ({current_row}, {current_column}) instead."
                    )
                else:
                    if AliquotLocation.objects.filter(box=box, row=start_row, column=start_column).exists():
                        current_row = start_row
                        current_column = start_column
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
                            first_slot = available_slots[0]
                            current_row = first_slot['row']
                            current_column = first_slot['column']
                            messages.warning(
                                self.request,
                                f"Requested position ({start_row}, {start_column}) is occupied and no slots available from that position. "
                                f"Using first available position ({current_row}, {current_column}) instead."
                            )
                    else:
                        current_row = start_row
                        current_column = start_column
            else:
                first_slot = available_slots[0]
                current_row = first_slot['row']
                current_column = first_slot['column']

            # Assign aliquots to box positions
            aliquots_assigned = 0
            max_retries = 3

            for aliquot in created_aliquots:
                slot_found = False
                retry_count = 0

                while not slot_found and retry_count < max_retries:
                    for row in range(current_row, box.rows + 1):
                        start_col = current_column if row == current_row else 1
                        for col in range(start_col, box.columns + 1):
                            try:
                                with transaction.atomic():
                                    if AliquotLocation.objects.filter(box=box, row=row, column=col).exists():
                                        continue

                                    AliquotLocation.objects.create(
                                        aliquot=aliquot,
                                        box=box,
                                        row=row,
                                        column=col,
                                    )

                                    # Update aliquot disposition to stored
                                    aliquot.disposition = stored_disposition
                                    aliquot.save()

                                    current_row = row
                                    current_column = col + 1
                                    slot_found = True
                                    aliquots_assigned += 1
                                    break
                            except IntegrityError:
                                continue
                        if slot_found:
                            break
                        current_column = 1

                    if not slot_found:
                        retry_count += 1
                        current_row = 1
                        current_column = 1

                if not slot_found:
                    messages.warning(
                        self.request,
                        f"Could not assign all aliquots. {aliquots_assigned} of {len(created_aliquots)} aliquots were assigned."
                    )
                    break

        return response
