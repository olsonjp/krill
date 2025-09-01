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
            defaults={
                'dark_mode': False,
                'email_notifications': True,
                'language': 'English',
                'auto_save_interval': '5 minutes',
                'data_retention_period': '90 days',
                'default_storage_location': 'Freezer A',
                'auto_archive_old_samples': False,
                'default_report_format': 'PDF',
                'auto_generate_reports': True,
                'display_name': request.user.first_name or request.user.username
            }
        )
        
        return JsonResponse({
            'success': True,
            'preferences': {
                'dark_mode': preference.dark_mode,
                'email_notifications': getattr(preference, 'email_notifications', True),
                'language': getattr(preference, 'language', 'English'),
                'auto_save_interval': getattr(preference, 'auto_save_interval', '5 minutes'),
                'data_retention_period': getattr(preference, 'data_retention_period', '90 days'),
                'default_storage_location': getattr(preference, 'default_storage_location', 'Freezer A'),
                'auto_archive_old_samples': getattr(preference, 'auto_archive_old_samples', False),
                'default_report_format': getattr(preference, 'default_report_format', 'PDF'),
                'auto_generate_reports': getattr(preference, 'auto_generate_reports', True),
                'display_name': getattr(preference, 'display_name', request.user.first_name or request.user.username)
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
        
        # Update fields if they exist in the model
        if 'dark_mode' in data:
            preference.dark_mode = data['dark_mode']
        
        # Update additional fields if they exist in the model
        # Note: These fields need to be added to the UserPreference model
        for field in ['email_notifications', 'language', 'auto_save_interval', 
                     'data_retention_period', 'default_storage_location', 
                     'auto_archive_old_samples', 'default_report_format', 
                     'auto_generate_reports', 'display_name']:
            if field in data and hasattr(preference, field):
                setattr(preference, field, data[field])
        
        preference.save()
        
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
