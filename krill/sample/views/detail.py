from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import IntegrityError, transaction
from django.contrib import messages
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm, AliquotMoveForm
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
            try:
                location = self.object.location
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
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        model_type = self.kwargs.get('type', 'sample')
        old_disposition = self.object.disposition if model_type == 'aliquot' else None
        form = self.get_form_class()(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            if model_type == 'aliquot':
                new_disp = form.cleaned_data.get('disposition')
                if (old_disposition and old_disposition.disposition_type == 'stored'
                        and new_disp and new_disp.disposition_type != 'stored'):
                    AliquotLocation.objects.filter(aliquot=self.object).delete()
            return redirect('sample:sample_list')
        return render(request, self.template_name, {'object': self.object, 'form': form})


@method_decorator(login_required, name='dispatch')
class AliquotDetailView(DetailView):
    model = Aliquot
    template_name = 'sample/tube_detail.html'
    context_object_name = 'aliquot'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aliquot = self.object
        # Add forms to context for editing and moving
        context['form'] = AliquotForm(instance=aliquot)
        context['move_form'] = AliquotMoveForm()
        # Get storage location if aliquot is stored
        try:
            location = aliquot.location
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
        old_disposition = self.object.disposition  # capture before form.is_valid() mutates instance
        form = AliquotForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            # If changing from stored to non-stored, remove storage location
            new_disp = form.cleaned_data.get('disposition')
            if (old_disposition and old_disposition.disposition_type == 'stored'
                    and new_disp and new_disp.disposition_type != 'stored'):
                AliquotLocation.objects.filter(aliquot=self.object).delete()
            return redirect('sample:aliquot_detail', pk=self.object.pk)
        else:
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context)

    def _handle_move(self, request):
        """Handle move form submission"""
        move_form = AliquotMoveForm(request.POST)
        if move_form.is_valid():
            stored_disposition, _ = AliquotDisposition.objects.get_or_create(
                name='Stored',
                defaults={'disposition_type': 'stored'}
            )

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

                    # Remove any existing location for this aliquot first
                    AliquotLocation.objects.filter(aliquot=self.object).delete()

                    # Create new location atomically
                    AliquotLocation.objects.create(
                        aliquot=self.object,
                        box=box,
                        row=row,
                        column=column,
                    )

                    # Update aliquot disposition to stored (within transaction)
                    if self.object.disposition != stored_disposition:
                        self.object.disposition = stored_disposition
                        self.object.save()
            except IntegrityError:
                if AliquotLocation.objects.filter(aliquot=self.object).exists():
                    messages.error(
                        request,
                        "This aliquot already has a location. "
                        "This may be due to a concurrent assignment. Please try again."
                    )
                else:
                    messages.error(
                        request,
                        f"Position ({row}, {column}) is already occupied. Please select a different position."
                    )
                context = self.get_context_data()
                context['move_form'] = move_form
                return render(request, self.template_name, context)

            messages.success(
                request,
                f"Aliquot moved to position ({row}, {column}) in {box.name}."
            )
            return redirect('sample:aliquot_detail', pk=self.object.pk)
        else:
            context = self.get_context_data()
            context['move_form'] = move_form
            return render(request, self.template_name, context)

    def _handle_checkout(self, request):
        """Handle checkout action - change disposition to 'in_use'"""
        was_stored = self.object.disposition.disposition_type == 'stored'

        in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

        self.object.disposition = in_use_disposition
        self.object.save()

        # Remove storage location if aliquot was stored
        if was_stored:
            AliquotLocation.objects.filter(aliquot=self.object).delete()

        return redirect('sample:aliquot_detail', pk=self.object.pk)
