from django.conf import settings

from person.models import UserPreference, SiteConfiguration


def support_email(request):
    """Expose the support address (settings.SUPPORT_EMAIL) to templates."""
    return {'support_email': settings.SUPPORT_EMAIL}


def site_configuration(request):
    return {'site_config': SiteConfiguration.load()}


def user_preferences(request):
    """Add user preferences to template context"""
    if request.user.is_authenticated:
        try:
            preference = UserPreference.objects.get(user=request.user)
            return {'user_preference': preference}
        except UserPreference.DoesNotExist:
            # Create default preference if it doesn't exist
            preference = UserPreference.objects.create(
                user=request.user,
                dark_mode=False
            )
            return {'user_preference': preference}
    return {'user_preference': None}
