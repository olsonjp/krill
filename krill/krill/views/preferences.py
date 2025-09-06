from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
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

@login_required
@require_http_methods(["GET"])
def get_user_preferences(request):
    """Get all user preferences"""
    try:
        preference, created = UserPreference.objects.get_or_create(
            user=request.user,
            defaults={'dark_mode': False}
        )

        return JsonResponse({
            'success': True,
            'preferences': {
                'dark_mode': preference.dark_mode,
                'display_name': request.user.first_name or request.user.username
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_http_methods(["POST"])
def save_user_preferences(request):
    """Save all user preferences"""
    try:
        data = json.loads(request.body)

        # Get or create user preference
        preference, created = UserPreference.objects.get_or_create(
            user=request.user,
            defaults={'dark_mode': False}
        )

        # Update dark mode if provided
        if 'dark_mode' in data:
            preference.dark_mode = data['dark_mode']
            preference.save()

        # Update display name (user's first_name field)
        if 'display_name' in data:
            request.user.first_name = data['display_name']
            request.user.save()

        return JsonResponse({
            'success': True,
            'message': 'Preferences saved successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
