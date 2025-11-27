from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import IntegrityError, transaction
from django.contrib import messages
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation, AliquotTube
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm, AliquotTubeForm, AliquotTubeMoveForm
from ..models.aliquot import AliquotDisposition

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
            stored_tubes = tubes.filter(disposition__disposition_type='stored')
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
            return redirect('sample:sample_list')
        return render(request, self.template_name, {'object': self.object, 'form': form})

@method_decorator(login_required, name='dispatch')
class TubeDetailView(DetailView):
    model = AliquotTube
    template_name = 'sample/tube_detail.html'
    context_object_name = 'tube'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tube = self.object
        # Add forms to context for editing and moving
        context['form'] = AliquotTubeForm(instance=tube)
        context['move_form'] = AliquotTubeMoveForm()
        # Get storage location if tube is stored
        if tube.disposition.disposition_type == 'stored':
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action', 'edit')

        if action == 'move':
            return self._handle_move(request)
        elif action == 'checkout':
            return self._handle_checkout(request)
        else:
            return self._handle_edit(request)

    def _handle_edit(self, request):
        """Handle edit form submission"""
        form = AliquotTubeForm(request.POST, instance=self.object)
        if form.is_valid():
            old_disposition = self.object.disposition
            form.save()
            # If changing from stored to non-stored, remove storage location
            if old_disposition.disposition_type == 'stored' and form.cleaned_data['disposition'].disposition_type != 'stored':
                AliquotLocation.objects.filter(
                    aliquot=self.object.aliquot,
                    tube_number=self.object.tube_number
                ).delete()
            return redirect('sample:tube_detail', pk=self.object.pk)
        else:
            # If form is invalid, re-render with errors
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context)

    def _handle_move(self, request):
        """Handle move form submission"""
        move_form = AliquotTubeMoveForm(request.POST)
        if move_form.is_valid():
            # Ensure tube is in stored disposition
            stored_disposition, _ = AliquotDisposition.objects.get_or_create(
                name='Stored',
                defaults={'disposition_type': 'stored'}
            )
            if self.object.disposition != stored_disposition:
                self.object.disposition = stored_disposition
                self.object.save()

            # Remove any existing location for this tube
            AliquotLocation.objects.filter(
                aliquot=self.object.aliquot,
                tube_number=self.object.tube_number
            ).delete()

            # Create new location with race condition handling
            box = move_form.cleaned_data['box']
            row = move_form.cleaned_data['row']
            column = move_form.cleaned_data['column']

            try:
                with transaction.atomic():
                    # Check if position is already occupied within transaction
                    if AliquotLocation.objects.filter(box=box, row=row, column=column).exists():
                        messages.error(
                            request,
                            f"Position ({row}, {column}) is already occupied. Please select a different position."
                        )
                        context = self.get_context_data()
                        context['move_form'] = move_form
                        return render(request, self.template_name, context)

                    # Create location atomically
                    AliquotLocation.objects.create(
                        aliquot=self.object.aliquot,
                        box=box,
                        row=row,
                        column=column,
                        tube_number=self.object.tube_number
                    )
            except IntegrityError:
                # Race condition: position was occupied between check and create
                messages.error(
                    request,
                    f"Position ({row}, {column}) is already occupied. Please select a different position."
                )
                context = self.get_context_data()
                context['move_form'] = move_form
                return render(request, self.template_name, context)

            messages.success(
                request,
                f"Tube moved to position ({row}, {column}) in {box.name}."
            )
            return redirect('sample:tube_detail', pk=self.object.pk)
        else:
            # If form is invalid, re-render with errors
            context = self.get_context_data()
            context['move_form'] = move_form
            return render(request, self.template_name, context)

    def _handle_checkout(self, request):
        """Handle checkout action - change disposition to 'in_use'"""
        # Check if tube is currently stored
        was_stored = self.object.disposition.disposition_type == 'stored'

        # Get 'in_use' disposition
        in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

        # Change tube disposition to 'in_use'
        self.object.disposition = in_use_disposition
        self.object.save()

        # Remove storage location if tube was stored
        if was_stored:
            AliquotLocation.objects.filter(
                aliquot=self.object.aliquot,
                tube_number=self.object.tube_number
            ).delete()

        return redirect('sample:tube_detail', pk=self.object.pk)
