from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import IntegrityError, transaction
from .models.aliquot import Aliquot, AliquotLocation

# Global flag to control automatic behavior (kept for backward compatibility)
AUTO_CREATE_TUBES = False
AUTO_STORE_TUBES = False


def auto_store_aliquot_tubes(aliquot):
    """
    Automatically store an aliquot in the first available auto-store enabled box.
    Called explicitly when needed.
    """
    from storage.models import Box
    auto_store_boxes = Box.objects.filter(
        rack__shelf__device__auto_store_enabled=True
    ).order_by('id')
    for box in auto_store_boxes:
        available_slots = box.get_available_slots()
        if available_slots:
            for slot in available_slots:
                try:
                    with transaction.atomic():
                        if AliquotLocation.objects.filter(
                            box=box, row=slot['row'], column=slot['column']
                        ).exists():
                            continue
                        AliquotLocation.objects.create(
                            aliquot=aliquot,
                            box=box,
                            row=slot['row'],
                            column=slot['column'],
                        )
                        break
                except IntegrityError:
                    continue
            else:
                continue
            break
