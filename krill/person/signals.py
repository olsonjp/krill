from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserPreference

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create UserPreference when a new User is created."""
    if created:
        UserPreference.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    """Save UserPreference when User is saved."""
    instance.preference.save() 