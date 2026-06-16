from datetime import date, timedelta

from django.shortcuts import redirect, render
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone

from sample.models.sample import Sample
from sample.models.aliquot import AliquotLocation
from storage.models.storage import Box
from person.models import UserAuditLog, UserPreference, SiteConfiguration
from person.decorators import require_minimum_role

__all__ = (
    'HomeView',
    'ReportsView',
    'SettingsView',
    'dashboard_stats',
)

@method_decorator(login_required, name='dispatch')
class HomeView(View):
    template_name = 'krill/home.html'

    def get(self, request):
        # Get dashboard statistics
        stats = get_dashboard_statistics()
        # Get recent activity
        recent_activity = get_recent_activity()

        return render(request, self.template_name, {
            'stats': stats,
            'recent_activity': recent_activity,
        })

@login_required
def dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    stats = get_dashboard_statistics()
    return JsonResponse(stats)

def get_dashboard_statistics():
    """Calculate dashboard statistics from database"""
    try:
        # Active samples (non-deleted)
        active_samples = Sample.objects.count()
        # Storage usage calculation
        total_slots = 0
        used_slots = 0
        # Calculate total slots from all boxes
        boxes = Box.objects.all()
        for box in boxes:
            total_slots += box.rows * box.columns
        # Calculate used slots from aliquot locations
        used_slots = AliquotLocation.objects.count()
        # Calculate percentage
        storage_usage = 0
        if total_slots > 0:
            storage_usage = round((used_slots / total_slots) * 100)
        # Recent reports (using audit logs for now)
        # In a real system, you'd have a Report model
        recent_reports = UserAuditLog.objects.filter(
            action='report_generated',
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        # Alerts (using audit logs for now)
        # In a real system, you'd have an Alert model
        alerts = UserAuditLog.objects.filter(
            action__in=['alert_created', 'warning_created'],
            timestamp__gte=timezone.now() - timedelta(days=1)
        ).count()
        # Consumables stats (only when feature is enabled)
        low_stock_count = 0
        expiring_soon_count = 0
        site_config = SiteConfiguration.load()
        if site_config.consumables_enabled:
            from consumables.models.consumable import Consumable
            low_stock_count = Consumable.objects.low_stock().count()
            expiring_soon_count = Consumable.objects.active().filter(
                expiration_date__isnull=False,
                expiration_date__lte=date.today() + timedelta(days=30),
                expiration_date__gte=date.today(),
            ).count()

        return {
            'active_samples': active_samples,
            'storage_usage': storage_usage,
            'recent_reports': recent_reports,
            'alerts': alerts,
            'total_slots': total_slots,
            'used_slots': used_slots,
            'low_stock_count': low_stock_count,
            'expiring_soon_count': expiring_soon_count,
        }
    except Exception as e:
        # Return default values if there's an error
        return {
            'active_samples': 0,
            'storage_usage': 0,
            'recent_reports': 0,
            'alerts': 0,
            'total_slots': 0,
            'used_slots': 0,
            'low_stock_count': 0,
            'expiring_soon_count': 0,
        }

def get_recent_activity():
    """Get recent activity from audit logs"""
    try:
        recent_activities = UserAuditLog.objects.select_related('user').order_by('-timestamp')[:5]
        activities = []
        for activity in recent_activities:
            # Format the activity message based on action type
            if activity.action == 'sample_created':
                message = f"New sample added: {activity.target_name or 'Unknown'}"
            elif activity.action == 'sample_updated':
                message = f"Sample updated: {activity.target_name or 'Unknown'}"
            elif activity.action == 'sample_deleted':
                message = f"Sample archived: {activity.target_name or 'Unknown'}"
            elif activity.action == 'aliquot_created':
                message = f"New aliquot created: {activity.target_name or 'Unknown'}"
            elif activity.action == 'aliquot_updated':
                message = f"Aliquot updated: {activity.target_name or 'Unknown'}"
            else:
                message = f"{activity.action.replace('_', ' ').title()}: {activity.target_name or 'Unknown'}"
            # Calculate time ago
            time_diff = timezone.now() - activity.timestamp
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days != 1 else ''} ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                time_ago = "Just now"
            activities.append({
                'message': message,
                'time_ago': time_ago,
                'action_type': activity.action,
                'user': activity.user.username if activity.user else 'System',
                'target_id': activity.target_id,
                'target_type': activity.target_type or '',
            })
        return activities
    except Exception as e:
        # Return default activities if there's an error
        return [
            {
                'message': 'System initialized',
                'time_ago': 'Just now',
                'action_type': 'system_init',
                'user': 'System',
                'target_id': None,
                'target_type': '',
            }
        ]

@method_decorator(login_required, name='dispatch')
class ReportsView(View):
    template_name = 'krill/reports.html'

    def get(self, request):
        return render(request, self.template_name)
@method_decorator(login_required, name='dispatch')
class SettingsView(View):
    template_name = 'krill/settings.html'

    def get(self, request):
        user_preference, _ = UserPreference.objects.get_or_create(
            user=request.user,
            defaults={'dark_mode': False}
        )
        return render(request, self.template_name, {
            'user_preference': user_preference,
            'site_config': SiteConfiguration.load(),
        })

    def post(self, request):
        from person.models import UserRole
        user_role = UserRole.get_or_create_for_user(request.user)
        if user_role.role != 'lab_admin':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Only lab admins can change site configuration.")

        config = SiteConfiguration.load()
        consumables_enabled = request.POST.get('consumables_enabled') == 'on'
        consumables_ordering_enabled = (
            request.POST.get('consumables_ordering_enabled') == 'on'
            and consumables_enabled
        )
        config.consumables_enabled = consumables_enabled
        config.consumables_ordering_enabled = consumables_ordering_enabled
        config.updated_by = request.user
        config.save()

        UserAuditLog.log_action(
            user=request.user,
            action='update',
            target_type='SiteConfiguration',
            target_id=config.pk,
            target_name='Site Configuration',
            details={
                'consumables_enabled': consumables_enabled,
                'consumables_ordering_enabled': consumables_ordering_enabled,
            },
            request=request,
        )

        from django.contrib import messages
        messages.success(request, 'Site configuration saved.')
        return redirect('settings')
