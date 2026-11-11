from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import IntegrityError, transaction
from django.contrib import messages
from django.utils import timezone
from ..models.sample import Sample
from ..models.aliquot import Aliquot, AliquotType, AliquotLocation
from ..models.source import Source
from ..forms import SampleForm, AliquotForm, AliquotTypeForm, SourceForm, AliquotMoveForm
from ..models.aliquot import AliquotDisposition
from person.models import SiteConfiguration, UserAuditLog
from .. import low_count
from .next_url import safe_next

def remaining_aliquots(sample):
    """The aliquots of a sample that are still stored (disposition Stored; a box position is not required).

    This is the same count the low-count alerts use.
    """
    return (
        Aliquot.objects.filter(
            sample=sample,
            deleted=False,
            disposition__disposition_type='stored',
        )
        .select_related(
            'aliquot_type',
            'location__box__rack__shelf__device',
        )
        .order_by('sample_date', 'id')
    )


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
        if context['model_type'] == 'sample':
            remaining = list(remaining_aliquots(self.object))
            context['remaining_aliquots'] = remaining
            context['remaining_count'] = len(remaining)
            counted = Sample.objects.with_stored_count().get(pk=self.object.pk)
            config = SiteConfiguration.load()
            warn, alert = low_count.levels_for(counted, config)
            context['low_count'] = {
                'count': counted.stored_count,
                'warn': warn,
                'alert': alert,
                'state': low_count.state_for(counted, config),
                'enabled': counted.low_count_check,
            }
        # Add storage location information for aliquots
        if self.kwargs.get('type') == 'aliquot':
            context['children'] = self.object.children.select_related('aliquot_type', 'disposition')
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

    def get_queryset(self):
        return Aliquot.objects.select_related(
            'sample',
            'aliquot_type',
            'disposition',
            'location__box__rack__shelf__device',
            'parent__sample',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aliquot = self.object
        # Add forms to context for editing and moving
        context['form'] = AliquotForm(instance=aliquot)
        context['move_form'] = AliquotMoveForm()
        context['children'] = aliquot.children.select_related('aliquot_type', 'disposition')
        context['excluded_form_fields'] = ['count', 'assign_to_box', 'box', 'start_row', 'start_column']
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
        elif action == 'done':
            return self._handle_done(request)
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

    def _handle_done(self, request):
        """The aliquot is used up and no child is being recorded: mark it Exhausted."""
        if self.object.disposition and self.object.disposition.disposition_type == 'in_use':
            self.object.mark_exhausted()
            UserAuditLog.log_action(
                user=request.user,
                action='aliquot_updated',
                target_type='Aliquot',
                target_id=self.object.id,
                target_name=str(self.object),
                details={'disposition': self.object.disposition.name, 'source': 'done'},
                request=request,
            )
        return redirect(safe_next(request, reverse('sample:aliquot_detail', kwargs={'pk': self.object.pk})))

    def _handle_checkout(self, request):
        """Handle checkout action - change disposition to 'in_use'"""
        was_stored = self.object.disposition and self.object.disposition.disposition_type == 'stored'
        if not was_stored:
            # Another person may have checked it out since this page was loaded: do not take it over
            return redirect(safe_next(request, reverse('sample:aliquot_detail', kwargs={'pk': self.object.pk})))

        in_use_disposition, _ = AliquotDisposition.objects.get_or_create(
            name='In Use',
            defaults={'disposition_type': 'in_use'}
        )

        self.object.disposition = in_use_disposition
        self.object.checked_out_by = request.user
        self.object.checked_out_at = timezone.now()
        self.object.save()

        # Remove storage location if aliquot was stored
        if was_stored:
            AliquotLocation.objects.filter(aliquot=self.object).delete()

        return redirect(safe_next(request, reverse('sample:aliquot_detail', kwargs={'pk': self.object.pk})))
