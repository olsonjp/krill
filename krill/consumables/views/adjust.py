from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from ..models.consumable import Consumable
from person.models import UserAuditLog
from person.decorators import require_minimum_role
from .mixins import consumables_enabled_required


@login_required
@consumables_enabled_required
@require_minimum_role('lab_member')
def consumable_adjust(request, pk):
    if request.method != 'POST':
        return redirect(reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': pk}))

    obj = get_object_or_404(Consumable, pk=pk, deleted=False)

    try:
        delta = Decimal(request.POST.get('delta', '0'))
    except InvalidOperation:
        delta = Decimal('0')

    note = request.POST.get('note', '')
    new_quantity = max(Decimal('0'), obj.quantity + delta)
    obj.quantity = new_quantity
    obj.save(update_fields=['quantity', 'updated_at'])

    UserAuditLog.log_action(
        user=request.user,
        action='update',
        target_type='Consumable',
        target_id=obj.pk,
        target_name=str(obj),
        details={'delta': str(delta), 'new_quantity': str(new_quantity), 'note': note},
        request=request,
    )
    return redirect(reverse('consumables:detail', kwargs={'type': 'consumable', 'pk': pk}))
