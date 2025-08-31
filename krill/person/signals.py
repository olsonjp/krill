from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserRole, UserPreference

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_role(sender, instance, created, **kwargs):
    """Automatically create UserRole when a User is created"""
    if created:
        # Determine the appropriate role based on user permissions
        if instance.is_superuser:
            role = 'lab_admin'
        elif instance.is_staff:
            role = 'lab_manager'
        else:
            role = 'viewer'
        
        UserRole.objects.create(
            user=instance,
            role=role,
            department='',
            lab_unit=''
        )


@receiver(post_save, sender=User)
def create_user_preference(sender, instance, created, **kwargs):
    """Automatically create UserPreference when a User is created"""
    if created:
        UserPreference.objects.create(
            user=instance,
            dark_mode=False
        )


@receiver(post_save, sender=User)
def update_user_role_on_superuser_change(sender, instance, **kwargs):
    """Update UserRole when superuser status changes"""
    if not kwargs.get('created', False):  # Only for updates, not creation
        try:
            user_role = instance.role
            if instance.is_superuser and user_role.role != 'lab_admin':
                user_role.role = 'lab_admin'
                user_role.save()
            elif not instance.is_superuser and instance.is_staff and user_role.role == 'viewer':
                user_role.role = 'lab_manager'
                user_role.save()
        except UserRole.DoesNotExist:
            # If no role exists, create one
            if instance.is_superuser:
                role = 'lab_admin'
            elif instance.is_staff:
                role = 'lab_manager'
            else:
                role = 'viewer'
            
            UserRole.objects.create(
                user=instance,
                role=role,
                department='',
                lab_unit=''
            ) 