from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse

from ..models.consumable import Consumable
from ..models.consumable_type import ConsumableType
from ..models.location import ConsumableRoom, ConsumableLocation
from ..models.vendor import Vendor
from ..forms import (
    ConsumableForm, ConsumableTypeForm, VendorForm,
    ConsumableRoomForm, ConsumableLocationForm,
)
from person.models import UserAuditLog
from .mixins import ConsumablesEnabledMixin


@method_decorator(login_required, name='dispatch')
class ConsumablesDetailView(ConsumablesEnabledMixin, DetailView):
    template_name = 'consumables/detail.html'

    def _model_type(self):
        return self.kwargs.get('type', 'consumable')

    def get_object(self):
        pk = self.kwargs['pk']
        t = self._model_type()
        if t == 'type':
            return get_object_or_404(ConsumableType, pk=pk)
        if t == 'vendor':
            return get_object_or_404(Vendor, pk=pk)
        if t == 'room':
            return get_object_or_404(ConsumableRoom, pk=pk)
        if t == 'location':
            return get_object_or_404(ConsumableLocation, pk=pk)
        return get_object_or_404(Consumable, pk=pk, deleted=False)

    def get_form_class(self):
        t = self._model_type()
        if t == 'type':
            return ConsumableTypeForm
        if t == 'vendor':
            return VendorForm
        if t == 'room':
            return ConsumableRoomForm
        if t == 'location':
            return ConsumableLocationForm
        return ConsumableForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        t = self._model_type()
        context['model_type'] = t
        form_class = self.get_form_class()
        if t == 'consumable':
            context['form'] = ConsumableForm(instance=self.object)
            # Build display list of spec fields zipped with values
            schema = self.object.consumable_type.spec_schema or []
            specs_display = [
                {'label': s['label'], 'value': self.object.specs.get(s['name'])}
                for s in schema
            ]
            context['specs_display'] = specs_display
            context['is_low_stock'] = self.object.is_low_stock
            context['is_expired'] = self.object.is_expired
        else:
            context['form'] = form_class(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        t = self._model_type()
        form_class = self.get_form_class()
        form = form_class(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            UserAuditLog.log_action(
                user=request.user,
                action='update',
                target_type=type(self.object).__name__,
                target_id=self.object.pk,
                target_name=str(self.object),
                request=request,
            )
            return redirect(f"{reverse('consumables:list')}?type={t}")
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
