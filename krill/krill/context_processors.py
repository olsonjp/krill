from person.models import UserPreference, SiteConfiguration


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
