from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models.aliquot import Aliquot, AliquotLocation, AliquotTube

@receiver(post_save, sender=Aliquot)
def create_aliquot_tubes(sender, instance, created, **kwargs):
    """
    Create individual tube instances when an aliquot is created.
    """
    if created and not hasattr(instance, '_tubes_created'):
        # Get the default disposition (usually "Stored")
        from .models.aliquot import AliquotDisposition
        default_disposition = AliquotDisposition.objects.get(dispositionType='stored')
        
        # Create individual tube instances
        for tube_number in range(1, instance.quantity + 1):
            AliquotTube.objects.create(
                aliquot=instance,
                tube_number=tube_number,
                disposition=default_disposition
            )
        
        # Mark as processed to prevent infinite loops
        instance._tubes_created = True

@receiver(post_save, sender=AliquotTube)
def auto_store_aliquot_tube(sender, instance, created, **kwargs):
    """
    Automatically store individual tubes in auto-store enabled boxes.
    Only stores tubes with "Stored" disposition.
    """
    if created and not hasattr(instance, '_auto_store_processed'):
        # Only auto-store if disposition is "Stored"
        if instance.disposition.dispositionType != 'stored':
            return
            
        # Check if tube already has a storage location (using the old model structure)
        if AliquotLocation.objects.filter(aliquot=instance.aliquot, tube_number=instance.tube_number).exists():
            return
        
        # Find available auto-store boxes
        from storage.models import Box
        
        auto_store_boxes = Box.objects.filter(
            rack__shelf__device__auto_store_enabled=True
        ).order_by('id')
        
        for box in auto_store_boxes:
            available_slots = box.get_available_slots()
            if available_slots:
                # Store tube in first available slot (using the old model structure)
                slot = available_slots[0]
                AliquotLocation.objects.create(
                    aliquot=instance.aliquot,
                    box=box,
                    row=slot['row'],
                    column=slot['column'],
                    tube_number=instance.tube_number
                )
                break
        
        # Mark as processed to prevent infinite loops
        instance._auto_store_processed = True

@receiver(pre_save, sender=AliquotTube)
def store_old_disposition(sender, instance, **kwargs):
    """
    Store the old disposition before saving to detect changes.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = AliquotTube.objects.get(pk=instance.pk)
            instance._old_disposition = old_instance.disposition.dispositionType
        except AliquotTube.DoesNotExist:
            instance._old_disposition = None

@receiver(post_save, sender=AliquotTube)
def handle_tube_disposition_change(sender, instance, created, **kwargs):
    """
    Handle disposition changes for individual tubes - remove storage locations when tube is no longer "Stored".
    """
    if not created and hasattr(instance, '_old_disposition'):
        old_disposition = instance._old_disposition
        new_disposition = instance.disposition.dispositionType
        
        # If disposition changed from "Stored" to something else, remove storage location
        if old_disposition == 'stored' and new_disposition != 'stored':
            # Remove storage location for this tube (using the old model structure)
            AliquotLocation.objects.filter(aliquot=instance.aliquot, tube_number=instance.tube_number).delete()

