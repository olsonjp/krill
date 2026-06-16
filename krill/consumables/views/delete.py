from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from ..models.consumable import Consumable
from person.models import UserAuditLog
from person.decorators import require_minimum_role
from .mixins import consumables_enabled_required


@login_required
@consumables_enabled_required
@require_minimum_role('lab_manager')
def consumable_delete(request, pk):
    if request.method != 'POST':
        return redirect(f"{reverse('consumables:list')}?type=consumable")
    obj = get_object_or_404(Consumable, pk=pk, deleted=False)
    obj.deleted = True
    obj.deleted_at = timezone.now()
    obj.save(update_fields=['deleted', 'deleted_at'])
    UserAuditLog.log_action(
        user=request.user,
        action='delete',
        target_type='Consumable',
        target_id=obj.pk,
        target_name=str(obj),
        request=request,
    )
    return redirect(f"{reverse('consumables:list')}?type=consumable")
