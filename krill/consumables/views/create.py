from django.views.generic.edit import CreateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.shortcuts import redirect

from ..forms import (
    ConsumableForm, ConsumableTypeForm, VendorForm,
    ConsumableRoomForm, ConsumableLocationForm,
)
from person.models import UserAuditLog
from person.decorators import require_minimum_role
from .mixins import ConsumablesEnabledMixin


@method_decorator(login_required, name='dispatch')
@method_decorator(require_minimum_role('lab_member'), name='dispatch')
class ConsumablesCreateView(ConsumablesEnabledMixin, CreateView):
    template_name = 'consumables/create.html'

    def _model_type(self):
        return self.request.GET.get('type', 'consumable')

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass selected consumable_type to ConsumableForm via initial so
        # _resolve_type can pick it up when rendering on GET.
        if self._model_type() == 'consumable':
            ctype_id = self.request.GET.get('consumable_type')
            if ctype_id:
                kwargs.setdefault('initial', {})['consumable_type'] = ctype_id
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        t = self._model_type()
        context['model_type'] = t
        labels = {
            'consumable': 'Consumable',
            'type': 'Consumable Type',
            'vendor': 'Vendor',
            'room': 'Room',
            'location': 'Location',
        }
        context['model_name'] = labels.get(t, t.title())
        # For the spec field section in the template
        if t == 'consumable':
            context['spec_field_names'] = getattr(context['form'], 'spec_field_names', [])
        return context

    def get_success_url(self):
        return f"{reverse_lazy('consumables:list')}?type={self._model_type()}"

    def form_valid(self, form):
        response = super().form_valid(form)
        UserAuditLog.log_action(
            user=self.request.user,
            action='create',
            target_type=type(self.object).__name__,
            target_id=self.object.pk,
            target_name=str(self.object),
            request=self.request,
        )
        return response
