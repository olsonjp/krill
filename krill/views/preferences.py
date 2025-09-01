from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from person.models import UserPreference

@login_required
@require_http_methods(["POST"])
def toggle_theme(request):
    # Get or create the user's preference
    preference, created = UserPreference.objects.get_or_create(
        user=request.user,
        defaults={'dark_mode': False}
    )
    # Toggle the dark mode setting
    preference.dark_mode = not preference.dark_mode
    preference.save()
    return JsonResponse({
        'dark_mode': preference.dark_mode,
        'success': True
    }) 